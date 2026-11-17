"""Informers re-watching an API server whose overload protection queues them. Units: seconds;
work in seat-seconds.

Client (Kubernetes API concepts page, "Efficient detection of changes"): a watch ends after a
period drawn from watch_period; the client re-watches from its last resourceVersion. If the
server answers after the retained history has passed (retention, 5 minutes by default for
etcd 3), the answer is 410 Gone and the client must LIST, then watch from the fresh version.
Server (API Priority and Fairness): requests beyond the concurrency limit queue; a LIST
occupies seats in proportion to the objects it returns. Modeled as one priority level whose
fair queuing among identical flows is FIFO, drained at `capacity` seat-seconds per second.

simulate() is the idealized server: a queue with no wait limit. simulate_limited() adds the two
mechanisms the documentation's queue leaves to the implementation. The API server removes a
queued request after min(remaining deadline / 4, 1 minute), 15 s at the default 60 s request
timeout, and answers 429 (server/filters/priority-and-fairness.go, getRequestWaitContext). The
client-go Reflector then backs off before retrying, with one delay function per Reflector shared
by watch retries, failed LISTs and the relist after a 410: 0.8 s doubling to a 30 s cap, each
delay jittered to [d, 2d), the sequence reset when more than 2 minutes have passed since its last
reset (tools/cache/reflector.go; apimachinery wait.Backoff and backoffManager).
"""
import heapq
import random
from dataclasses import dataclass, field
from typing import NamedTuple, Optional


def simulate(cost_list, clients=2000, cost_watch=0.05, capacity=100.0, retention=300.0,
             watch_period=(300.0, 600.0), forced=1.0, spread=0.0, hours=8, seed=1):
    """Run from a trigger at t = 0 in which a fraction `forced` of clients must LIST (a
    controller restart, an outage longer than the retention), their LISTs arriving uniformly
    over `spread` seconds; the other clients are mid-watch. Returns (LISTs completed in each
    hour, largest queue delay seen in seconds)."""
    rng = random.Random(seed)
    events, free_at = [], [0.0]

    def submit(t, cost):
        start = max(t, free_at[0])
        free_at[0] = start + cost / capacity
        return free_at[0]

    horizon = hours * 3600.0
    per_hour, worst = [0] * hours, 0.0
    for i in range(clients):
        if rng.random() < forced:
            heapq.heappush(events, (rng.uniform(0.0, spread) if spread else 0.0, 1, i))
        else:
            heapq.heappush(events, (rng.uniform(*watch_period), 0, i))
    while events:
        t, is_list, i = heapq.heappop(events)
        if t >= horizon:
            break
        worst = max(worst, free_at[0] - t)
        done = submit(t, cost_list if is_list else cost_watch)
        if is_list:
            if done < horizon:
                per_hour[int(done // 3600)] += 1
            heapq.heappush(events, (done + rng.uniform(*watch_period), 0, i))
        elif done - t > retention:
            heapq.heappush(events, (done, 1, i))
        else:
            heapq.heappush(events, (done + rng.uniform(*watch_period), 0, i))
    return per_hour, worst


class ReflectorBackoff:
    """client-go's Reflector delay function: wait.Backoff{Duration 0.8 s, Cap 30 s, Factor 2,
    Jitter 1.0} behind a backoffManager with a 2-minute reset interval. The manager resets to the
    initial backoff when more than the interval has passed since its last reset."""

    def __init__(self, rng, init=0.8, cap=30.0, factor=2.0, jitter=1.0, reset=120.0, start=-1e18):
        self.rng, self.init, self.cap, self.factor, self.jitter, self.reset = rng, init, cap, factor, jitter, reset
        self.duration, self.last_start = init, start

    def step(self, now):
        if now - self.last_start > self.reset:
            self.duration, self.last_start = self.init, now
        d = self.duration
        self.duration = min(self.duration * self.factor, self.cap)
        return d + self.rng.random() * self.jitter * d if self.jitter > 0 else d


@dataclass
class SplitController:
    """Moves lists to a priority level of their own while 410s persist, as a FlowSchema matching the verb list
    does in API Priority and Fairness; requests already admitted keep their place. Every `period` seconds it
    counts the 410s of the last `window` seconds; above `on_rate` per second it gives lists `share` of the
    capacity and watches the rest, and it moves them back once `hold` seconds have passed with no 410."""
    on_rate: float
    window: float
    period: float
    hold: float
    share: float
    switches: int = field(default=0, init=False)
    split_seconds: float = field(default=0.0, init=False)
    _recent: list = field(default_factory=list, init=False)
    _next: float = field(default=0.0, init=False)
    _last_gone: float = field(default=-1e18, init=False)
    _since: Optional[float] = field(default=None, init=False)

    def observe_gone(self, t: float) -> None:
        self._recent.append(t)
        self._last_gone = t

    def tick(self, t: float, server: 'Server') -> None:
        """Every evaluation due by time t, in order."""
        while self._next <= t:
            self._recent = [x for x in self._recent if x > self._next - self.window]
            if server.share is None and len(self._recent) / self.window > self.on_rate:
                server.divide(self.share)
                self.switches += 1
                self._since = self._next
            elif server.share is not None and self._next - self._last_gone >= self.hold:
                server.merge()
                self.split_seconds += self._next - self._since
            self._next += self.period

    def seconds_split(self, end: float, server: 'Server') -> float:
        return self.split_seconds + (end - self._since if server.share is not None else 0.0)


class Server:
    """One priority level's capacity, served first come first served; divided, lists get `share` of it and
    watches the rest, each in its own order."""

    def __init__(self, capacity: float):
        self.capacity, self.share = capacity, None
        self.free_at = self.free_watch = self.free_list = 0.0

    def start(self, t: float, is_list: bool) -> float:
        if self.share is None:
            return max(t, self.free_at)
        return max(t, self.free_list if is_list else self.free_watch)

    def rate(self, is_list: bool) -> float:
        if self.share is None:
            return self.capacity
        return self.capacity * (self.share if is_list else 1.0 - self.share)

    def finish(self, done: float, is_list: bool) -> None:
        if self.share is None:
            self.free_at = done
        elif is_list:
            self.free_list = done
        else:
            self.free_watch = done

    def divide(self, share: float) -> None:
        self.share, self.free_watch, self.free_list = share, self.free_at, self.free_at

    def merge(self) -> None:
        self.share, self.free_at = None, max(self.free_watch, self.free_list)


class LimitedRun(NamedTuple):
    """What simulate_limited records: LISTs completed in each hour; re-watches answered 410; requests rejected;
    the longest delay from a watch's end to its re-watch being served; the fewest and most consecutive
    rejections behind a 410, None if there was none; the attempts and rejections of re-watches and of LISTs
    after the first hour, {'watch': (attempts, rejections), 'list': (...)}; and the detail per client and
    over time: 'gone' and 'lists' per client, 'last_gone', 'gone_per_hour', 'worst_admitted_wait',
    'switches', 'stranded' (clients answered 410 more than an hour before the end and not listed since),
    'forced' per client, and 'split_seconds'."""
    per_hour: list
    gone: int
    rejected: int
    worst: float
    streaks: Optional[tuple]
    steady: dict
    detail: dict


def _trigger(rng: random.Random, clients: int, forced: float, spread: float, waves, watch_period) -> tuple[list, list, list]:
    """The first event of each client: a LIST the trigger forces, at a wave's time or spread over `spread`
    seconds, or the end of a watch already running. Returns (events, forced per client, watch ends)."""
    events, forced_by, watch_end = [], [False] * clients, [0.0] * clients
    for i in range(clients):
        if waves is not None:
            x, at = rng.random(), None
            for t, share in waves:
                if x < share:
                    at = t
                    break
                x -= share
            if at is not None:
                heapq.heappush(events, (at, 1, i))
                forced_by[i] = True
                continue
        elif rng.random() < forced:
            heapq.heappush(events, (rng.uniform(0.0, spread) if spread else 0.0, 1, i))
            forced_by[i] = True
            continue
        watch_end[i] = rng.uniform(*watch_period)
        heapq.heappush(events, (watch_end[i], 0, i))
    return events, forced_by, watch_end


def simulate_limited(cost_list, clients=2000, cost_watch=0.05, capacity=100.0, retention=300.0,
                     watch_period=(300.0, 600.0), forced=1.0, spread=0.0, hours=8, seed=1,
                     wait_limit=15.0, waves=None, controller=None, backoff_raised=False,
                     cost_switch=None) -> LimitedRun:
    """As simulate(), with the queue wait limit and the Reflector's backoff. A request is admitted iff the work
    ahead of it lets it start within wait_limit; otherwise it is rejected with 429 when the limit expires, and
    its client backs off and retries the same request. A re-watch served more than `retention` after its watch
    ended gets 410; the client then backs off once (the Reflector's loop delay) and LISTs. A LIST served starts
    a watch at once.

    cost_list is one cost or one per client. waves, if given, replaces forced and spread: a sequence of (time,
    share), each client falling in at most one wave with that wave's share as its probability; the informers
    that resume against one restarted server of several are one wave. controller is a SplitController, or the
    dict of its five settings. backoff_raised starts every backoff at its cap, memory the queue's state does
    not show. cost_switch, (time, cost), makes every LIST cost the new value from that time on."""
    rng = random.Random(seed)
    if isinstance(controller, dict):
        controller = SplitController(**controller)
    cost_of = (lambda k: cost_list[k]) if isinstance(cost_list, (list, tuple)) else (lambda k: cost_list)
    gone_by, lists_by = [0] * clients, [0] * clients
    last_gone = 0.0
    backoff = [ReflectorBackoff(rng) for _ in range(clients)]
    if backoff_raised:
        for b in backoff:
            b.duration, b.last_start = b.cap, 0.0
    events, forced_by, watch_end = _trigger(rng, clients, forced, spread, waves, watch_period)
    server = Server(capacity)
    horizon = hours * 3600.0
    per_hour, gone, rejected, worst = [0] * hours, 0, 0, 0.0
    streak, streaks = [0] * clients, []
    steady = {'watch': [0, 0], 'list': [0, 0]}
    gone_per_hour, worst_admitted, pending = [0] * hours, 0.0, {}
    t = 0.0
    while events:
        t, is_list, i = heapq.heappop(events)
        if t >= horizon:
            break
        if controller is not None:
            controller.tick(t, server)
        cap, start = server.rate(is_list), server.start(t, is_list)
        if t >= 3600.0:
            steady['list' if is_list else 'watch'][0] += 1
        if start - t > wait_limit:
            if t >= 3600.0:
                steady['list' if is_list else 'watch'][1] += 1
            rejected += 1
            streak[i] += 1
            heapq.heappush(events, (t + wait_limit + backoff[i].step(t + wait_limit), is_list, i))
            continue
        worst_admitted = max(worst_admitted, start - t)
        list_cost = cost_switch[1] if cost_switch is not None and start >= cost_switch[0] else cost_of(i)
        done = start + (list_cost if is_list else cost_watch) / cap
        server.finish(done, is_list)
        run, streak[i] = streak[i], 0
        if is_list:
            if done < horizon:
                per_hour[int(done // 3600)] += 1
                lists_by[i] += 1
                pending.pop(i, None)
            watch_end[i] = done + rng.uniform(*watch_period)
            heapq.heappush(events, (watch_end[i], 0, i))
            continue
        worst = max(worst, done - watch_end[i])
        if done - watch_end[i] > retention:
            gone += 1
            gone_by[i] += 1
            last_gone = done
            if controller is not None:
                controller.observe_gone(done)
            pending.setdefault(i, done)
            if done < horizon:
                gone_per_hour[int(done // 3600)] += 1
            streaks.append(run)
            heapq.heappush(events, (done + backoff[i].step(done), 1, i))
        else:
            watch_end[i] = done + rng.uniform(*watch_period)
            heapq.heappush(events, (watch_end[i], 0, i))
    return LimitedRun(per_hour, gone, rejected, worst, (min(streaks), max(streaks)) if streaks else None,
                      {k: tuple(v) for k, v in steady.items()},
                      {'gone': gone_by, 'lists': lists_by, 'last_gone': last_gone, 'gone_per_hour': gone_per_hour,
                       'worst_admitted_wait': worst_admitted,
                       'switches': controller.switches if controller is not None else 0,
                       'stranded': sum(1 for x in pending.values() if x < horizon - 3600.0), 'forced': forced_by,
                       'split_seconds': controller.seconds_split(min(t, horizon), server) if controller is not None else 0.0})



def simulate_fair(cost_list, clients=2000, cost_watch=0.05, capacity=100.0, retention=300.0,
                  watch_period=(300.0, 600.0), forced=1.0, spread=0.0, hours=8, seed=1,
                  wait_limit=15.0, queues=64, hand=6, queue_limit=50):
    """As simulate_limited(), with APF's fair queuing in place of one FIFO queue, at the defaults
    of the "system" priority level that the "system-nodes" flow schema uses (64 queues, hand size
    6, queue length limit 50; apis/flowcontrol/bootstrap/default.go). Each client is its own flow
    and is dealt a fixed hand of queues; a request joins the shortest queue in its hand, is
    rejected at once if that queue is full, and is removed and rejected if it waits longer than
    wait_limit. When the server frees, it serves the head of the non-empty queue that has received
    the least work, a queue that has been empty starting from the least work among busy queues.
    Service is one request at a time at `capacity` seat-seconds per second."""
    rng = random.Random(seed)
    cost_of = (lambda k: cost_list[k]) if isinstance(cost_list, (list, tuple)) else (lambda k: cost_list)
    gone_by, lists_by = [0] * clients, [0] * clients
    backoff = [ReflectorBackoff(rng) for _ in range(clients)]
    hands = [rng.sample(range(queues), hand) for _ in range(clients)]
    watch_end = [0.0] * clients
    qs = [[] for _ in range(queues)]          # FIFO lists of request ids
    head = [0] * queues                        # index of the first live entry
    live = [0] * queues                        # requests waiting in each queue
    served = [0.0] * queues
    reqs = {}                                  # id -> [queue, arrival, is_list, client, alive]
    events, rid = [], 0                        # (time, order, kind, payload)
    runs = [0] * clients                       # rejections behind the request now in service
    order = 0

    def push(t, kind, payload):
        nonlocal order
        order += 1
        heapq.heappush(events, (t, order, kind, payload))

    for i in range(clients):
        if rng.random() < forced:
            push(rng.uniform(0.0, spread) if spread else 0.0, 'arrive', (i, True))
        else:
            watch_end[i] = rng.uniform(*watch_period)
            push(watch_end[i], 'arrive', (i, False))
    horizon = hours * 3600.0
    per_hour, gone, rejected, worst = [0] * hours, 0, 0, 0.0
    busy_until = 0.0
    idle = True
    streak, streaks = [0] * clients, []

    def reject(t, i, is_list):
        nonlocal rejected
        rejected += 1
        streak[i] += 1
        push(t + backoff[i].step(t), 'arrive', (i, is_list))

    def dispatch(t):
        nonlocal idle, busy_until
        cands = [q for q in range(queues) if live[q]]
        if not cands:
            idle = True
            return
        q = min(cands, key=lambda x: served[x])
        while True:
            r = qs[q][head[q]]
            head[q] += 1
            if r in reqs:              # entries removed on timeout are skipped
                break
        _, arr, is_list, i, _ = reqs.pop(r)
        live[q] -= 1
        runs[i], streak[i] = streak[i], 0
        cost = cost_of(i) if is_list else cost_watch
        served[q] += cost
        busy_until = t + cost / capacity
        idle = False
        push(busy_until, 'done', (i, is_list))

    while events:
        t, _, kind, payload = heapq.heappop(events)
        if t >= horizon:
            break
        if kind == 'arrive':
            i, is_list = payload
            q = min(hands[i], key=lambda x: live[x])
            if live[q] >= queue_limit:
                reject(t, i, is_list)
                continue
            if live[q] == 0:
                busy = [served[x] for x in range(queues) if live[x]]
                if busy:
                    served[q] = max(served[q], min(busy))
            rid += 1
            reqs[rid] = [q, t, is_list, i, True]
            qs[q].append(rid)
            live[q] += 1
            push(t + wait_limit, 'timeout', rid)
            if idle:
                dispatch(t)
        elif kind == 'timeout':
            r = reqs.get(payload)
            if r is not None and r[4]:
                r[4] = False
                live[r[0]] -= 1
                del reqs[payload]
                reject(t, r[3], r[2])
        else:
            i, is_list = payload
            if is_list:
                per_hour[int(t // 3600)] += 1
                lists_by[i] += 1
                watch_end[i] = t + rng.uniform(*watch_period)
                push(watch_end[i], 'arrive', (i, False))
            else:
                worst = max(worst, t - watch_end[i])
                if t - watch_end[i] > retention:
                    gone += 1
                    gone_by[i] += 1
                    streaks.append(runs[i])
                    push(t + backoff[i].step(t), 'arrive', (i, True))
                else:
                    watch_end[i] = t + rng.uniform(*watch_period)
                    push(watch_end[i], 'arrive', (i, False))
            dispatch(t)
    return per_hour, gone, rejected, worst, (min(streaks), max(streaks)) if streaks else None, {'gone': gone_by, 'lists': lists_by}


def simulated_no_bookmark_gone(rate, history, watches=20000, watch_period=(300.0, 600.0), seed=1):
    """Share of re-watches answered 410 when nothing sends bookmarks and the server answers at once:
    one informer whose selector sees Poisson events at `rate`; each watch lasts a uniform period; the
    resume version is that of the last event, or of the last list; a re-watch whose version is older
    than `history` is answered 410 and the informer lists at once, which refreshes the version."""
    rng = random.Random(seed)
    t, last, gone = 0.0, 0.0, 0
    next_event = rng.expovariate(rate) if rate > 0 else float('inf')
    for _ in range(watches):
        end = t + rng.uniform(*watch_period)
        while next_event <= end:
            last = next_event
            next_event += rng.expovariate(rate)
        if end - last > history:
            gone += 1
            last = end
        t = end
    return gone / watches
