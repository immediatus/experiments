"""Fluid simulation of one Deployment under the ported HPA, with client timeouts,
retries, wasted work, an optional admission bound, and a choice of scaling signal.

Kubernetes facts come from hpa_port.py (v1.34.0 source). Everything below is a model
assumption, stated so a reader can change it:
  * 1 s steps, fluid FIFO queue, one core serves RATE req/s, request = 1 core.
  * A new pod serves traffic `dead` s after creation; the HPA counts it ready one
    metric `window` later. Metrics are means over the last `window` seconds.
  * A request waiting `timeout` s is abandoned by its client and retried at once (after a backoff
    if `backoff` is set), up to `retries` times. With `zombie` True the server still spends the work on the abandoned
    copy when it reaches it (the client's departure is invisible to the server).
  * Admission bound `shed_s`: arriving work is rejected beyond what would bring the queue
    to `shed_s` seconds of current capacity. Rejections cost no CPU. Rejected
    requests retry like timed-out ones when `retry_rejects` is True.
  * Scale-down removes pending pods first, then the newest serving pods, at once.
Signals: 'cpu' (resource utilization), 'ingress' (arrivals at the load balancer per
pod, retries included), 'first' (first-attempt arrivals per pod), 'pair' (both external
metrics on one HPA, which takes the larger recommendation).
"""
import math
from collections import deque

from hpa_port import SYNC, Normalizer, external_per_pod_replicas, resource_replicas

RATE = 100.0                                             # requests a second one core serves


def run(mult, signal='cpu', dead=90, window=30, limit=1.0, target=50, n0=10,
        max_replicas=10 ** 6, timeout=None, retries=0, zombie=True, shed_s=None,
        retry_rejects=True, horizon=3600, trace=None, backoff=0, budget=None, eta=1.0, series=None):
    """Simulate one Deployment for `horizon` seconds and return what happened.

    Load: before any change the service runs n0 pods at `target` percent utilization, so the
    base demand is n0 * RATE * target / 100 requests a second; `mult(t)` multiplies it at second t.

    mult          function of the second, the demand as a multiple of the base (see step)
    signal        'cpu', 'ingress', 'first' or 'pair' (module docstring)
    dead          seconds from ordering a pod until it serves (the dead time; 90 in the series)
    window        metric window in seconds; a new pod counts as ready one window after it serves
    limit         CPU limit over CPU request: a saturated pod serves `limit` cores
    target        utilization target in percent; also sets the base demand
    n0            pods before any change
    max_replicas  the replica ceiling
    timeout       seconds a client waits before abandoning an attempt (None: never)
    retries       retries after the first attempt
    zombie        True: the server still serves abandoned attempts (retry debt)
    shed_s        admission bound in seconds of current capacity (None: no bound)
    retry_rejects True: a rejected attempt is retried like a timed-out one
    backoff       retry n waits backoff * 2**(n-1) seconds
    budget        retries a second capped at budget * first attempts a second (None: no cap)
    eta           share of its nominal rate a saturated pod still serves
    trace         list to receive (t, ordered pods, ready pods, backlog) at every sync
    series        list to receive (t, serving pods, demand, ingress, good, wasted, backlog,
                  abandoned work) every second

    Returns a dict. Work is in requests: first (first attempts), good (served for a waiting
    client), wasted (abandoned work served), lost (attempts given up for good), rejected
    (refused by the bound, retried or not). Times are seconds from 0: t_cap (first second
    capacity meets a raised demand, else None), last_bad (last second with a timeout, a loss
    or a backlog, else None). Also peak and final pods, peak_backlog, peak_ingress, pod_s
    (pod-seconds), and the scales a caller needs to express results in its own units: base
    (the base demand) and per_pod (what one pod carries at the target).
    """
    base = n0 * RATE * target / 100.0
    per_pod_target = RATE * target / 100.0
    groups = [[-10 ** 9, -10 ** 9, n0]]                  # [serve_from, hpa_ready_from, count]
    norm = Normalizer(max_replicas=max_replicas)
    hist = deque(maxlen=window)
    fresh = deque()                                      # [arrival_t, amount, attempt]
    zombie_work = 0.0
    future = {}                                          # second -> [(amount, attempt)]
    tokens = [0.0]

    def sched(now, amt, att):
        """Queue a retry. budget caps retries per second at budget * first-attempt rate;
        backoff delays attempt n by backoff * 2**(n-1) seconds. Returns the amount dropped."""
        dropped = 0.0
        if budget is not None:
            ok = min(amt, tokens[0])
            tokens[0] -= ok
            dropped = amt - ok
            amt = ok
        if amt > 0:
            future.setdefault(now + 1 + int(backoff * 2 ** (att - 1)), []).append((amt, att))
        return dropped
    backlog = 0.0
    o = dict(peak=n0, peak_backlog=0.0, lost=0.0, wasted=0.0, good=0.0, first=0.0,
             last_bad=None, t_cap=None, pod_s=0.0, peak_ingress=0.0, rejected=0.0,
             base=base, per_pod=per_pod_target)
    for t in range(horizon):
        lam = base * mult(t)
        serving = sum(g[2] for g in groups if g[0] <= t)
        total = sum(g[2] for g in groups)
        # eta < 1: a saturated pod (work is queued) serves only eta of its nominal rate
        # while still burning its full CPU limit (thrash, context switching, memory pressure).
        eff = RATE * (eta if (backlog > 1e-6 or zombie_work > 1e-6) else 1.0)
        cap = serving * eff * limit
        arrivals = [(lam, 0)] + future.pop(t, [])
        tokens[0] = (budget or 0.0) * lam
        ingress = math.fsum(a for a, _ in arrivals)
        o['first'] += lam
        o['peak_ingress'] = max(o['peak_ingress'], ingress)
        bad = False
        for amt, att in arrivals:
            if shed_s is not None:
                room = max(0.0, cap * shed_s - backlog)
                rej = max(0.0, amt - room)
                amt -= rej
                if rej > 0:
                    o['rejected'] += rej
                    d = sched(t, rej, att + 1) if (retry_rejects and att < retries) else rej
                    if d > 0:
                        o['lost'] += d
                        bad = True
            if amt > 0:
                fresh.append([t, amt, att])
                backlog += amt
        if timeout is not None:
            while fresh and t - fresh[0][0] >= timeout:
                _, amt, att = fresh.popleft()
                backlog -= amt
                if zombie:
                    zombie_work += amt
                d = sched(t, amt, att + 1) if att < retries else amt
                if d > 0:
                    o['lost'] += d
                    bad = True
        left = cap
        z = min(zombie_work, left)
        zombie_work -= z
        left -= z
        o['wasted'] += z
        good = 0.0
        while fresh and left > 1e-9:
            c = fresh[0]
            take = min(c[1], left)
            c[1] -= take
            left -= take
            good += take
            backlog -= take
            if c[1] <= 1e-9:
                fresh.popleft()
        o['good'] += good
        if series is not None:
            series.append((t, serving, lam, ingress, good, z, backlog, zombie_work))
        backlog = max(0.0, backlog) if fresh else 0.0
        o['peak_backlog'] = max(o['peak_backlog'], backlog + zombie_work)
        if backlog > 1e-6 or zombie_work > 1e-6:
            bad = True
        if bad:
            o['last_bad'] = t
        if o['t_cap'] is None and mult(t) > 1.0 and cap >= lam:
            o['t_cap'] = t
        o['pod_s'] += total
        hist.append(((cap - left) / eff / serving * 1000.0, ingress, lam))
        if t % SYNC == 0:
            ready = sum(g[2] for g in groups if g[1] <= t)
            n = len(hist)
            if signal == 'cpu':
                desired, _ = resource_replicas(total, [math.fsum(h[0] for h in hist) / n] * ready,
                                               total - ready, 1000, target)
            elif signal == 'pair':
                desired = max(external_per_pod_replicas(total, math.fsum(h[k] for h in hist) / n, per_pod_target)
                              for k in (1, 2))
            else:
                k = 1 if signal == 'ingress' else 2
                desired = external_per_pod_replicas(total, math.fsum(h[k] for h in hist) / n, per_pod_target)
            new = norm(t, total, desired)
            if new > total:
                groups.append([t + dead, t + dead + window, new - total])
            elif new < total:
                drop = total - new
                for g in sorted(groups, key=lambda g: -g[0]):
                    d = min(g[2], drop)
                    g[2] -= d
                    drop -= d
                    if drop == 0:
                        break
                groups = [g for g in groups if g[2] > 0]
            o['peak'] = max(o['peak'], new)
            if trace is not None:
                trace.append((t, new, ready, round(backlog + zombie_work)))
        o['final'] = sum(g[2] for g in groups)
    return o


def step(k, at=60, until=None):
    """Demand multiplier: k from second `at` until second `until` (None: for good), else 1."""
    def mult(t):
        return k if (t >= at and (until is None or t < until)) else 1.0
    return mult


def pods_needed(o, k):
    """Pods that carry k times the base demand of run result o at its target."""
    return math.ceil(k * (o['base'] / o['per_pod']))
