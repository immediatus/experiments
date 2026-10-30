"""Queue-length (backlog) scaling through the ported HPA, as KEDA configures it by default.

KEDA facts used (docs v2.19): a trigger's metric reaches the HPA as an external metric of type
AverageValue by default; the HPA then computes ceil(metric / target per pod)
(GetExternalPerPodMetricReplicas, ported in hpa_port.py); Kafka lagThreshold defaults to 10.
Model assumptions: fluid backlog L' = lam - c * ready_pods (floored at 0); a new pod consumes
DEAD seconds after it is created; scale-down removes pods at once; 1 s steps; HPA sync 15 s;
no retries or timeouts (a message queue keeps its messages).
Theory for comparison: with N = L/T acting after a pure delay tau, L' = lam - (c/T) L(t - tau)
is stable iff (c/T) * tau < pi/2, i.e. T > (2/pi) * c * tau.
"""
import math
import random

from hpa_port import SYNC, Normalizer, external_per_pod_replicas


def run(T, lam0=50.0, lam1=200.0, c=10.0, dead=90, window=300, horizon=14400, step_at=600,
        n_min=1, n_max=100, tol=0.1, poll=15, noise=0.0, rebalance=0, seed=1, trace=None):
    """Simulate a consumer scaled on its backlog for `horizon` seconds.

    T             backlog threshold per pod (messages); T / c is the standing delay
    lam0, lam1    demand before and after the step at second `step_at` (messages a second)
    c             messages a second one pod consumes
    dead          seconds from ordering a pod until it consumes
    window        downscale stabilization window in seconds
    n_min, n_max  replica floor and ceiling
    tol           tolerance band of the replica calculation
    poll          seconds between refreshes of the backlog metric
    noise         demand is multiplied by a lognormal factor of that sigma, redrawn every 60 s,
                  and arrivals each second are Poisson-like around it
    rebalance     after any change in the number of consuming pods, no pod consumes for that
                  many seconds (a consumer-group rebalance)
    seed          seed of the noise
    trace         list to receive (pods ordered, pods consuming, backlog) every second

    noise and rebalance default to off, which reproduces the noise-free tables. Returns a dict
    over the last hour: n_lo, n_hi, p05, p95 and mean of the pods ordered, l_lo and l_hi of the
    backlog, flips (changes of the pod count); and over the run after the step: peak pods; and
    need, the pods that carry lam1.
    """
    rng = random.Random(seed)
    factor = 1.0
    paused_until = -1
    last_ready = None
    groups = [[-10 ** 9, max(n_min, math.ceil(lam0 / c))]]     # [consuming_from, count]
    norm = Normalizer(min_replicas=n_min, max_replicas=n_max, window=window)
    L = T * lam0 / c                                            # start at the equilibrium backlog
    seen = L
    hist = []
    for t in range(horizon):
        lam = lam1 if t >= step_at else lam0
        if noise:
            if t % 60 == 0:
                factor = math.exp(rng.gauss(-noise * noise / 2, noise))
            lam = max(0.0, rng.gauss(lam * factor, math.sqrt(lam * factor)))
        ready = sum(g[1] for g in groups if g[0] <= t)
        total = sum(g[1] for g in groups)
        if rebalance and last_ready is not None and ready != last_ready:
            paused_until = t + rebalance
        last_ready = ready
        L = max(0.0, L + lam - (0.0 if t < paused_until else c * ready))
        if t % poll == 0:
            seen = L                                            # metric refreshed every `poll` seconds
        if t % SYNC == 0:
            desired = external_per_pod_replicas(total, seen, T, tol) if total > 0 else math.ceil(seen / T)
            new = norm(t, total, desired)
            if new > total:
                groups.append([t + dead, new - total])
            elif new < total:
                drop = total - new
                for g in sorted(groups, key=lambda g: -g[0]):
                    d = min(g[1], drop)
                    g[1] -= d
                    drop -= d
                    if drop == 0:
                        break
                groups = [g for g in groups if g[1] > 0]
        hist.append((total, ready, L))
    if trace is not None:
        trace.extend(hist)
    tail = hist[-3600:]
    ns = [h[0] for h in tail]
    ls = [h[2] for h in tail]
    srt = sorted(ns)
    peak = max(h[0] for h in hist[step_at:])
    return dict(n_lo=min(ns), n_hi=max(ns), l_lo=min(ls), l_hi=max(ls), peak=peak,
                p05=srt[len(srt) // 20], p95=srt[-len(srt) // 20], mean=sum(ns) / len(ns),
                need=math.ceil(lam1 / c), flips=sum(1 for a, b in zip(ns, ns[1:]) if a != b))
