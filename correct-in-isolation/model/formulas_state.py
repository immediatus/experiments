"""Closed forms of Part 3, a shared state: the backlog a forced list builds against the history, the client's
backoff and the runs of rejections behind a 410, the mean-field fold, and API Priority and Fairness's levels.

Every input is a documented contract or a named parameter; defaults are the series' specimen."""
import collections
import itertools
import math


def backlog(cost_list, clients, capacity):
    """Seconds of queue the forced LISTs build: clients x cost_list / capacity."""
    return clients * cost_list / capacity


def second_wave(cost_list, clients, capacity, retention, shortest_watch):
    """A trigger forcing every client to LIST starts a second wave only if the backlog outlasts the
    shortest watch period plus the retention: the first client served re-watches after at least
    the shortest watch period and is answered with 410 only if the queue still holds more than
    the retention."""
    return backlog(cost_list, clients, capacity) > shortest_watch + retention


def failed_state_delay(cost_list, clients, capacity, mean_watch):
    """Queue delay at which a storm of LISTs sustains itself: every client cycles through a watch
    period, a queued re-watch and a queued LIST, so clients / (mean_watch + 2 D) LISTs per
    second must fill capacity / cost_list, D = (backlog - mean_watch) / 2."""
    return (backlog(cost_list, clients, capacity) - mean_watch) / 2.0


def failed_state_possible(cost_list, clients, capacity, retention, mean_watch):
    """Necessary condition for a self-sustaining storm: its delay must exceed the retention, or
    re-watches would succeed and leave it, backlog > mean_watch + 2 retention."""
    return failed_state_delay(cost_list, clients, capacity, mean_watch) > retention


def rejections_before_gone(retention, wait_limit=15.0, cap=30.0, jitter=1.0):
    """Fewest consecutive rejections behind a re-watch answered 410, whatever its client's backoff
    state: a request waits at most wait_limit before it is served or rejected, and each rejection
    adds at most wait_limit plus the largest jittered backoff, (1 + jitter) cap, so the delay
    passes the retention only after ceil((retention - wait_limit) / (wait_limit + (1 + jitter) cap))."""
    return math.ceil((retention - wait_limit) / (wait_limit + (1 + jitter) * cap))


def fresh_rejections_to_pass(retention, wait_limit=15.0, init=0.8, cap=30.0, factor=2.0, reset=120.0, raised=False,
                             longest=18):
    """For a client whose backoff starts fresh (or at its cap, raised): (fewest, most) consecutive rejections
    behind a re-watch answered 410. After n rejections the next attempt starts at A_n, the sum over
    rejections of wait_limit plus the Reflector's delay, doubling from init to cap and reset to init whenever
    more than `reset` seconds have passed since the last reset; each delay is jittered to between one and
    two times its base, and the attempt is served within wait_limit of A_n. A 410 is possible once
    A_n + wait_limit exceeds the retention, and certain once A_n does. Both are taken over every pattern of
    the jitter's extremes, because the reset is measured in elapsed time: a smaller jitter early postpones the
    reset and lets the capped delays run longer, so the largest jitter throughout is not the fastest way to
    a 410 (the P model in p/ found this)."""
    def first(jitters, slack):
        t, d, last = 0.0, (cap if raised else init), 0.0
        for n, j in enumerate(jitters, 1):
            t += wait_limit
            if t - last > reset:
                d, last = init, t
            t += d * j
            d = min(d * factor, cap)
            if t + slack > retention:
                return n
        return longest + 1
    patterns = list(itertools.product((1.0, 2.0), repeat=longest))
    return min(first(p, wait_limit) for p in patterns), max(first(p, 0.0) for p in patterns)


def backoff_schedule(raised=False, jitter=1.5, length=60, wait_limit=15.0, init=0.8, cap=30.0, factor=2.0,
                     reset=120.0):
    """The Reflector's delays between consecutive rejections of one request: b_i follows rejection i. Each
    rejection costs wait_limit, then the delay, doubling from init to cap and reset to init whenever more
    than `reset` seconds have passed since the last reset. jitter multiplies every delay: 1 is the base,
    2 the largest, 1.5 the mean of the client's jitter. raised starts the run at the cap, as for a client
    whose last run of rejections ended moments ago: the history statistic of Part 3's seam."""
    t, d, last, out = 0.0, (cap if raised else init), 0.0, []
    for _ in range(length):
        t += wait_limit
        if t - last > reset:
            d, last = init, t
        out.append(d * jitter)
        t += d * jitter
        d = min(d * factor, cap)
    return out


def gone_after(schedule, retention=300.0, wait_limit=15.0):
    """Fewest consecutive rejections after which the next attempt, served within wait_limit, can come
    later than the retention: the run a re-watch on this schedule must lose to be answered 410."""
    t = 0.0
    for j, b in enumerate(schedule):
        if t + wait_limit > retention:
            return j
        t += wait_limit + b
    return len(schedule)


def meanfield_onset(raised=False, clients=2000, capacity=100.0, retention=300.0, mean_watch=450.0,
                    wait_limit=15.0, grid=10000, admitted_wait=0.0):
    """Mean-field reading of the storm onset. In a saturated storm every attempt is rejected with
    probability p, independently. A re-watch is answered 410 when it loses n* = gone_after(schedule)
    rejections in a row, so a share phi = p^n* of cycles ends in a LIST. A trying client spends
    E = sum_i p^(i+1) (wait_limit + b_i) before it is served, for the re-watch and again for the LIST, which
    follows one more delay. Saturation (Proposition 21's argument) needs phi B = E[cycle] =
    mean_watch + E + phi (b_0 + E). admitted_wait is the queue wait of the attempt that is finally served,
    once for the re-watch and once more for the LIST; it lies between 0 and wait_limit. For a given p this fixes B; the least B over p is the fold, below which
    the equation has no saturated solution: a saddle-node. Returns (B*, list cost at the fold, p at the
    fold, n*). The fold moves with the schedule the runs start on: history the queue does not show."""
    b = backoff_schedule(raised=raised, length=80, wait_limit=wait_limit)
    n = gone_after(b, retention, wait_limit)
    best = None
    for k in range(grid // 2, grid - 1):
        p = k / grid
        phi = p ** n
        trying = math.fsum(p ** (i + 1) * (wait_limit + bi) for i, bi in enumerate(b))
        cycle = mean_watch + trying + admitted_wait + phi * (b[0] + trying + admitted_wait)
        B = cycle / phi
        if best is None or B < best[0]:
            best = (B, p)
    return best[0], best[0] * capacity / clients, best[1], n


def saturated_storm_possible(cost_list, clients, capacity, retention, mean_watch):
    """Necessary condition for a storm that keeps the server saturated with LISTs, under any order
    of service. Let a fraction f of client cycles end in a LIST. Saturation makes the LIST rate
    f clients / E[cycle] equal capacity / cost_list, so E[cycle] = f B with B the backlog
    clients x cost_list / capacity; every cycle holds a watch, mean_watch on average, and every
    cycle that ends in a LIST a re-watch delayed past the retention, so E[cycle] >= mean_watch +
    f retention. Together B >= mean_watch / f + retention >= mean_watch + retention."""
    return backlog(cost_list, clients, capacity) > mean_watch + retention


def failed_list_rate(cost_list, capacity):
    """LISTs per second in the failed state: all capacity spent on LISTs, capacity / cost_list."""
    return capacity / cost_list


def watch_cache_span(rate, fresh=75.0, lower=100, upper=100 * 1024, horizon=None):
    """Seconds of history the API server's watch cache holds at a steady event rate, replaying its
    resize rule event by event (apiserver storage/cacher/watch_cache_history.go): before each new
    event, a full cache doubles if its oldest event is younger than the fresh duration (75 s by
    default, a minute of bookmarks plus 15 s) and halves if the first event of its newest quarter
    is older than it; a full cache then drops its oldest event. Returns the span from the oldest
    retained event to the newest, the history a re-watch through the cache has."""
    dt = 1.0 / rate
    n = int((horizon if horizon is not None else max(4000.0, 4.0 * upper * dt)) * rate)
    cap, cache = lower, collections.deque()
    for i in range(n):
        t = i * dt
        if len(cache) == cap:
            if t - cache[0] < fresh and cap < upper:
                cap = min(cap * 2, upper)
            elif t - cache[len(cache) - cap // 4] > fresh and cap > lower:
                cap = max(cap // 2, lower)
                while len(cache) > cap:
                    cache.popleft()
        if len(cache) == cap:
            cache.popleft()
        cache.append(t)
    return cache[-1] - cache[0]


def pages_before_expiry(history, wait_limit=15.0, page_size=500):
    """The most pages of a paginated list that can be served before its first page's resourceVersion
    leaves the history, when every page waits the full queue wait limit (the best case a saturated queue
    allows), and the objects they hold at the pager's default page size of 500. A longer list's
    continuation is answered 410, and the pager falls back to one unpaginated list."""
    pages = int(history // wait_limit)
    return pages, pages * page_size


def no_bookmark_gone_probability(rate, history):
    """Without bookmarks a re-watch resumes from the version of the last event its selector delivered
    (or of the last list). When every watch lasts at least `history`, the re-watch is answered 410
    exactly when no matching event came in the last `history` seconds: exp(-rate * history) for events
    arriving at `rate` per second."""
    return math.exp(-rate * history)


def no_bookmark_load(rate, history, clients=2000, cost_list=100.0, capacity=100.0, mean_watch=450.0):
    """The share of the server's capacity that re-lists take with no trigger at all when nothing sends
    bookmarks: every watch ends once per mean watch period, a share exp(-rate * history) of re-watches
    is answered 410 and lists, so the load is the forced backlog clients * cost_list / capacity times
    that share over the mean watch period. Above 1 the server is overloaded by the steady state alone."""
    return clients * cost_list / capacity * no_bookmark_gone_probability(rate, history) / mean_watch


# API Priority and Fairness defaults (apiserver apis/flowcontrol/bootstrap/default.go): nominal shares and
# hand size of the suggested queuing levels; the shares of every level, the mandatory exempt (0) and
# catch-all (5) included, sum to 245.
APF_LEVELS = {'system': (30, 6), 'node-high': (40, 6), 'leader-election': (10, 4), 'workload-high': (40, 6),
              'workload-low': (100, 6), 'global-default': (20, 6)}


APF_SHARE_SUM = 245


def level_limits(server_limit=600, levels=APF_LEVELS, share_sum=APF_SHARE_SUM):
    """Each queuing level's nominal concurrency limit and the most seats one request may take there:
    CL = ceil(server limit x shares / share sum) (apf_controller.go), and max seats = max(1,
    min(ceil(0.15 CL), CL / handSize)) with integer division. The server limit is the sum of
    --max-requests-inflight (400) and --max-mutating-requests-inflight (200)."""
    out = {}
    for name, (shares, hand) in levels.items():
        cl = math.ceil(server_limit * shares / share_sum)
        out[name] = (cl, max(1, min(math.ceil(cl * 0.15), cl // hand)))
    return out


def list_seats(objects, avg_bytes, from_cache=True, level_max=100):
    """Seats the size-based estimator charges a list (list_work_estimator.go, SizeBasedListCostEstimate):
    ceil(bytes / 100,000) with the bytes capped at 1,000,000 when the list is served from the watch
    cache, then at least 1 and at most the smaller of 100 (MaximumListSeatsLimit) and the level's
    maximum. The bytes are every stored object of the type: the estimator does not discount a
    selector for a list served from the cache."""
    memory = objects * avg_bytes
    if from_cache:
        memory = min(memory, 1_000_000)
    seats = math.ceil(memory / 100_000)
    return max(1, min(seats, 100, level_max))


def list_time_threshold(informers, seats, level_cl, backlog):
    """The execution time per list at which a full trigger's backlog N_I x seats x time / CL reaches
    `backlog` seconds: backlog x CL / (N_I x seats)."""
    return backlog * level_cl / (informers * seats)
