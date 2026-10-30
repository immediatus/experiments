"""Idealized backlog loop, to locate its stability boundary.

Reduced model. Backlog L, per-pod rate c, lag threshold T, demand lam. The recommendation is
r = L/T. The downscale window makes the desired count the maximum of r over the last W
seconds; the dead time makes the ready count the minimum of the desired count over the last
tau seconds (a pod counts only if it has been wanted for tau without interruption):

    N(t) = min over u in [t - tau, t] of ( max over v in [u - W, u] of L(v)/T ),   L' = lam - c N.

Around the equilibrium L* = T lam / c write x = (L - L*)/L*. The two filters commute with
adding a constant, so  x' = -k F[x]  with  k = c/T  and  F = min_tau(max_W(.)).
F is positively homogeneous, so growth or decay of a perturbation does not depend on its
size, and with time measured in units of tau the only parameters are  a = k*tau  and
w = W/tau.  This file finds, for each w, the largest a at which perturbations still decay.
No clamps, no sampling, no rounding: those belong to the deployed loop (backlog_sim.py).
"""
import math
from collections import deque


def growth(a, w, dt=0.004, cycles_time=400.0, start=-1.0):
    """Return the late/early amplitude ratio of x for x' = -a * min_1(max_w(x)), tau = 1."""
    n_tau = max(1, round(1.0 / dt))
    n_w = round(w / dt)
    steps = int(cycles_time / dt)
    x = start
    maxq = deque()          # indices with decreasing x: sliding max over n_w + 1 samples
    minq = deque()          # indices with increasing m: sliding min over n_tau + 1 samples
    xs = [0.0] * steps
    ms = [0.0] * steps
    amp_early = amp_late = 0.0
    q1, q2, q3 = steps // 4, steps // 2, 3 * steps // 4
    for i in range(steps):
        xs[i] = x
        while maxq and xs[maxq[-1]] <= x:
            maxq.pop()
        maxq.append(i)
        if maxq[0] < i - n_w:
            maxq.popleft()
        m = xs[maxq[0]]
        ms[i] = m
        while minq and ms[minq[-1]] >= m:
            minq.pop()
        minq.append(i)
        if minq[0] < i - n_tau:
            minq.popleft()
        f = ms[minq[0]]
        x += -a * f * dt
        ax = abs(x)
        if q1 <= i < q2:
            amp_early = max(amp_early, ax)
        elif i >= q3:
            amp_late = max(amp_late, ax)
        if ax > 1e12:
            return float('inf')
    if amp_early < 1e-12:
        return 0.0
    return amp_late / amp_early


def critical_a(w, lo=0.02, hi=8.0, iters=22, cycles_time=400.0):
    """Largest a = k*tau with decaying perturbations, by bisection on the growth ratio."""
    if growth(hi, w, cycles_time=cycles_time) < 1.0:
        return float('inf')
    for _ in range(iters):
        mid = math.sqrt(lo * hi)
        if growth(mid, w, cycles_time=cycles_time) < 1.0:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def step_response(a, w, dt=0.002, steps=30000, n_tau=500):
    """The loop after an upward step from rest, x(0) = -1, with tau = 1 (Proposition 5).

    Returns (largest overshoot of x above 0, number of steps at which the acting
    recommendation fell). Both are 0 when the loop rises monotonically and the window never
    acts. n_tau is the dead time in steps, 1 / dt.
    """
    n_w = round(w / dt)
    xs, ms, maxq, minq = [], [], deque(), deque()
    x, top, falls, prev = -1.0, -1.0, 0, None
    for i in range(steps):
        xs.append(x)
        while maxq and xs[maxq[-1]] <= x:
            maxq.pop()
        maxq.append(i)
        if maxq[0] < i - n_w:
            maxq.popleft()
        ms.append(xs[maxq[0]])
        while minq and ms[minq[-1]] >= ms[-1]:
            minq.pop()
        minq.append(i)
        if minq[0] < i - n_tau:
            minq.popleft()
        f = ms[minq[0]]
        if prev is not None and f < prev - 1e-12:
            falls += 1
        prev = f
        x += -a * f * dt
        top = max(top, x)
    return max(top, 0.0), falls
