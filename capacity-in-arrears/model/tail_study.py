"""Monte Carlo: overload factor K ~ Pareto(alpha), x_min 1.5, applied as a sustained step.
Reports how the tail of K maps onto recovery time and onto size (backlog, loss, overshoot)."""
import math
import random

from loop_sim import pods_needed, run, step


def q(v, p):
    """The p-quantile of v: the value at index floor(p n) of the sorted sample."""
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


def tail_index(v, frac=0.1):
    """Hill estimator on the top `frac` of the sample (at least 5 points); nan if undefined."""
    v = sorted(v, reverse=True)
    k = max(5, int(frac * len(v)))
    x = v[k]
    if x <= 0:
        return float('nan')
    d = math.fsum(math.log(v[i] / x) for i in range(k))
    return k / d if d > 0 else float('nan')


def study(alpha, n, **kw):
    """n sustained steps of size K ~ Pareto(alpha), seed 7, K capped at 2000, one hour each.

    kw passes through to loop_sim.run. Returns five lists, one entry per trial, in this order:
    K; seconds from the step until capacity meets it (the rest of the hour if never); peak
    backlog in seconds of the base demand; peak pods over the pods needed; work lost in
    seconds of the base demand.
    """
    rng = random.Random(7)
    ks, tc, bl, ov, lost = [], [], [], [], []
    for _ in range(n):
        k = 1.5 * (1 - rng.random()) ** (-1 / alpha)
        k = min(k, 2000.0)
        o = run(step(k), horizon=3600, **kw)
        ks.append(k)
        tc.append((o['t_cap'] or 3600) - 60)
        bl.append(o['peak_backlog'] / o['base'])
        ov.append(o['peak'] / pods_needed(o, k))
        lost.append(o['lost'] / o['base'])
    return ks, tc, bl, ov, lost
