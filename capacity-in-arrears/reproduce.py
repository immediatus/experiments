"""Every number quoted in the series, one section per table. Specimen: dead time 90 s.

    python3 reproduce.py                   every section          python3 reproduce.py T4   one section
    python3 reproduce.py --check           the tests, then every section against expected/results.txt
    python3 reproduce.py --figures         draw the SVG figures   python3 reproduce.py --figures --check   compare them

The command line is the repository's shared tools/harness.py; this file holds the sections.

Model assumptions are in docs/ASSUMPTIONS.md and model/; Kubernetes facts are in model/hpa_port.py
(v1.34.0); the closed-form results are in model/formulas.py.
"""
import cmath
import functools
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, p) for p in ('model', 'figures', os.path.join('..', 'tools'))]

import harness
from backlog_boundary import boundary, hunts, phi
from backlog_ideal import critical_a, growth, step_response
from backlog_sim import run as backlog_run
from formulas import (hottest_target, phi_harmonic_balance, recovery_long_spike, recovery_piecewise,
                      rounds, stale_gain_bound)
from hpa_port import external_per_pod_replicas, resource_replicas
from loop_sim import RATE, pods_needed, run, step
from request_sim import simulate
from setup_sim import erlang_c_mean_response, onoff_inf_mean_response
from setup_sim import simulate as setup_simulate
from tail_study import q, study, tail_index

DEAD = 90            # the specimen's dead time, seconds
H = 14400            # horizon of most runs: four hours
STEP = 60            # second at which every step and spike begins (loop_sim.step's default)
SPIKE = 300          # length of every spike, seconds
TIMEOUT = 10         # client timeout, seconds
MARGIN = 600         # a run still bad in its last ten minutes has not recovered


def stuck(o, horizon):
    """True if the run was still bad within MARGIN seconds of its end."""
    return o['last_bad'] is not None and o['last_bad'] >= horizon - MARGIN


def bad_until(o, since):
    """Seconds from `since` to the run's last bad second. Every caller's run goes bad, so a run
    that never did is an error, not a recovery time of zero."""
    if o['last_bad'] is None:
        raise ValueError('the run never went bad, so it has no recovery time')
    return o['last_bad'] - since


def to_capacity(o):
    """Seconds from the step until capacity met the raised demand; the run must have got there."""
    if o['t_cap'] is None:
        raise ValueError('capacity never met the demand')
    return o['t_cap'] - STEP


def stepped(o, k):
    """The demand during a k-fold step of run o, requests a second."""
    return k * o['base']


@functools.lru_cache(maxsize=None)
def saturated(k):
    """The saturated-CPU step run that T2, T34 and T46 all report: 10 pods at 50%, limit = request."""
    return run(step(k), 'cpu', dead=DEAD, horizon=H)


def naive(d, n=40):
    """The one-line ratio rule fed a replica count d syncs old (load 1000, 100 per pod, from 8 pods)."""
    N = [8.0] * (d + 1)
    for _ in range(n):
        N.append(N[-1] * 1000 / (N[-1 - d] * 100))
    return N[d + 1:]


def orders(k, n0, max_replicas=10 ** 6, until=900):
    """A k-fold step from n0 pods, and its orders: (seconds after the step, pods ordered, pods
    counted ready) at each change of the order, up to `until` seconds after the step."""
    tr = []
    o = run(step(k), 'cpu', dead=DEAD, n0=n0, max_replicas=max_replicas, horizon=H, trace=tr)
    seq = []
    for t, n, ready, _ in tr:
        if STEP <= t <= STEP + until and (not seq or seq[-1][1] != n):
            seq.append((t - STEP, n, ready))
    return o, seq


def backlog(delay, dead=DEAD, window=300, trace=None):
    """The deployed backlog loop of Part 2: 50 -> 200 pods needed, ceiling 2000, 20 h."""
    return backlog_run(round(delay * 10.0), lam0=500.0, lam1=2000.0, c=10.0, dead=dead, window=window,
                       horizon=72000, step_at=600, n_max=2000, trace=trace)


def t1():
    print('T1 textbook rule, replica count stale by d sync periods (load 1000, target 100 per pod, start 8 pods)')
    for d in (0, 1, 2, 3):
        tr = naive(d)
        print('  d=%d first 8: %s  late min %.3g max %.3g' % (d, [round(x, 1) for x in tr[:8]], min(tr[-12:]), max(tr[-12:])))


def t2():
    print('T2 saturated CPU, limit=request, target 50%: overload | predicted rounds | time to capacity | peak/need | peak backlog (s of base load)')
    for k in (3, 5, 10, 30, 100, 300):
        o = saturated(k)
        print('  %4dx | %d | %5d s | %.2f | %d' % (k, rounds(k), to_capacity(o), o['peak'] / pods_needed(o, k), o['peak_backlog'] / o['base']))


def t3():
    print('T3 non-saturating metric (limit 100x request): overload | peak/need')
    for k in (2, 10, 30):
        o = run(step(k), 'cpu', dead=DEAD, limit=100.0, horizon=H)
        print('  %3dx | %.2f' % (k, o['peak'] / pods_needed(o, k)))


def t4():
    print('T4 growth factor g=limit/(request*target), 30x step: limit | target | g | predicted rounds | time to capacity')
    for limit, target in ((1.0, 50), (1.0, 60), (1.0, 70), (1.0, 80), (2.0, 50), (4.0, 50), (1.0, 25)):
        g = limit / (target / 100.0)
        o = run(step(30), 'cpu', dead=DEAD, limit=limit, target=target, horizon=H)
        print('  %.0fx | %d%% | %.2f | %d | %d s' % (limit, target, g, rounds(30, target, limit), to_capacity(o)))


def t5():
    print('T5 sustained 10x, timeout 10 s, 2 retries, wasted work: signal | time to capacity | peak/need | first attempts lost (s of the stepped demand; "ongoing" if never healthy) | state at end')
    for sig in ('cpu', 'ingress', 'first'):
        o = run(step(10), sig, dead=DEAD, timeout=TIMEOUT, retries=2, horizon=H)
        bad = stuck(o, H)
        print('  %-8s | %5d s | %.2f | %s | %s' % (sig, to_capacity(o), o['peak'] / pods_needed(o, 10), 'ongoing, %.1f%% of all demand' % (100 * o['lost'] / o['first']) if bad else '%.0f s' % (o['lost'] / stepped(o, 10)), 'failed' if bad else 'healthy after %d s' % bad_until(o, STEP)))


def t6():
    print('T6 fixed capacity, 10x spike 300 s: rho | R | A*rho | predicted recovery | fluid | request-level (3 seeds)')
    for rho, R in ((0.5, 0), (0.25, 1), (0.3, 1), (0.2, 2), (0.4, 1), (0.5, 1), (0.5, 2), (0.4, 2)):
        a = (R + 1) * rho
        pred = recovery_long_spike(10, rho, R + 1, SPIKE)
        hor = 20000 if pred is None else int(pred * 1.6) + 3000
        o = run(step(10, until=STEP + SPIKE), 'cpu', target=int(round(rho * 100)), max_replicas=10, timeout=TIMEOUT, retries=R, horizon=hor)
        fl = 'stuck' if stuck(o, hor) else str(bad_until(o, STEP + SPIKE))
        des = []
        for s in range(3):
            last, _ = simulate(rho, R, s, horizon=float(hor))
            des.append('stuck' if last and last > hor - 60 else str(int(last - (STEP + SPIKE))))
        print('  %.2f | %d | %.2f | %s | %s | %s' % (rho, R, a, 'stuck' if pred is None else '%.0f' % pred, fl, ' '.join(des)))


def t7():
    print('T7 first-attempt signal, sustained 10x: target | retry policy | first attempts lost (s of the stepped demand) | state')
    for target, kw, lab in ((50, dict(retries=2), '2 retries'), (33, dict(retries=2), '2 retries'), (30, dict(retries=2), '2 retries'),
                            (25, dict(retries=2), '2 retries'), (50, dict(retries=2, backoff=5), '2 retries, backoff 5 s'),
                            (50, dict(retries=5, budget=0.2), 'budget 20%'), (50, dict(retries=5, budget=0.5), 'budget 50%')):
        o = run(step(10), 'first', dead=DEAD, target=target, timeout=TIMEOUT, horizon=H, **kw)
        bad = stuck(o, H)
        print('  %d%% | %-22s | %s | %s' % (target, lab, 'ongoing, %.1f%% of all demand' % (100 * o['lost'] / o['first']) if bad else '%.0f s' % (o['lost'] / stepped(o, 10)), 'failed' if bad else 'healthy after %d s' % bad_until(o, STEP)))


def t8():
    print('T8 admission bound 5 s, sustained 10x, 2 retries: signal | time to capacity | peak/need | first attempts lost (s of the stepped demand)')
    for sig in ('cpu', 'first'):
        o = run(step(10), sig, dead=DEAD, timeout=TIMEOUT, retries=2, shed_s=5, horizon=H)
        print('  %-6s | %d s | %.2f | %.0f s' % (sig, to_capacity(o), o['peak'] / pods_needed(o, 10), o['lost'] / stepped(o, 10)))


def t9():
    print('T9 Pareto overloads, 3000 trials: alpha | config | quantity | p50 | p90 | p99 | tail index')
    for alpha in (3.0, 1.5):
        for name, kw in (('no bound', dict(signal='cpu', dead=DEAD)),
                         ('bound 5 s cpu', dict(signal='cpu', dead=DEAD, timeout=TIMEOUT, retries=2, shed_s=5)),
                         ('bound 5 s first', dict(signal='first', dead=DEAD, timeout=TIMEOUT, retries=2, shed_s=5))):
            ks, tc, bl, ov, lost = study(alpha, 3000, **kw)
            for lab, v in (('K', ks), ('t_cap', tc), ('backlog', bl), ('lost', lost)):
                print('  %.1f | %-16s | %-8s | %.1f | %.1f | %.1f | %.2f' % (alpha, name, lab, q(v, .5), q(v, .9), q(v, .99), tail_index(v)))


def t10():
    print('T10 saturated pods serve eta of nominal rate: overload | eta | time to capacity | drained | peak/need')
    for k in (10, 30):
        for eta in (1.0, 0.8, 0.6, 0.4):
            o = run(step(k), 'cpu', dead=DEAD, eta=eta, horizon=H)
            print('  %3dx | %.1f | %d s | %d s | %.2f' % (k, eta, to_capacity(o), bad_until(o, STEP), o['peak'] / pods_needed(o, k)))


def t11():
    print('T11 idealized backlog loop: w = window / dead time | Phi = needed standing delay in dead times | 0.55*sqrt(w) | 0.62+0.255*ln(w)')
    for w in (0.5, 1.0, 2.0, 3.0, 10 / 3, 5.0, 10.0, 20.0, 40.0):
        print('  %5.2f | %.3f | %.3f | %.3f' % (w, 1 / critical_a(w), 0.55 * math.sqrt(w), 0.62 + 0.255 * math.log(w)))


def t12():
    print('T12 deployed backlog loop, 50 -> 200 pods needed, 20 h runs: dead | window | observed boundary T/c | tau*Phi(W/tau) | with 10 s sampling delay')
    errs = []
    for dead in (30, 60, 90, 180):
        for window in (60, 120, 300, 600):
            obs = boundary(dead, window)
            pred = (dead + 10) * phi((window + 10) / (dead + 10))
            errs.append(abs(pred - obs) / obs)
            print('  %4d | %4d | %6.1f s | %6.1f s | %6.1f s' % (dead, window, obs, dead * phi(window / dead), pred))
    print('  mean absolute error %.1f%%, largest %.1f%%' % (100 * math.fsum(errs) / len(errs), 100 * max(errs)))


def t13():
    print('T13 deployed backlog loop, dead 90 s, window 300 s, 200 pods needed; pods 5th..95th percentile (mean) in the last hour: T/c | noise-free | demand noise 10% | noise 30% | rebalance pause 10 s | pause 30 s | polling 30 s')
    for d in (40, 60, 80, 100, 120, 150, 200, 300):
        cells = []
        for kw in ({}, dict(noise=0.1), dict(noise=0.3), dict(rebalance=10), dict(rebalance=30), dict(poll=30)):
            o = hunts(d, 90, 300, **kw)[1]
            cells.append('%d..%d (%d)' % (o['p05'], o['p95'], o['mean']))
        print('  %4d | %s' % (d, ' | '.join(cells)))


def t14():
    print('T14 idealized backlog loop, long windows: growth of a disturbance over 3000 dead times (below 1 decays): w | a=0.36 | a=0.45 | a=0.60   (a = c*tau/T; 1/e = %.4f)' % (1 / math.e))
    for w in (20.0, 100.0, 400.0, 1000.0):
        cells = []
        for a in (0.36, 0.45, 0.60):
            g = growth(a, w, dt=0.004, cycles_time=3000.0)
            cells.append('grows' if g >= 1.0 else 'decays')
        print('  %6d | %s' % (w, ' | '.join(cells)))


def t15():
    print('T15 one-line ratio rule with a replica count d sync periods old, x[t+1] = x[t] - K x[t-d]: d | exact bound on K, 2 sin(pi/(2(2d+1))) | sufficient bound 1/(1+d) | the rule itself has K = 1')
    for d in range(0, 5):
        exact = stale_gain_bound(d)
        print('  %d | %.3f | %.3f | %s' % (d, exact, 1 / (1 + d), 'stable' if 1 < exact else ('marginal' if abs(exact - 1) < 1e-9 else 'unstable')))


def t16():
    print('T16 fixed 10 pods, 10x spike 300 s, retry budget beta (A = 1 + beta): rho | beta | A*rho | predicted recovery | fluid model')
    for rho in (0.5, 0.8):
        for beta in (0.1, 0.2, 0.5, 1.0):
            a = (1 + beta) * rho
            pred = recovery_long_spike(10, rho, 1 + beta, SPIKE)
            hor = 20000 if pred is None else int(pred * 1.3) + 3000
            o = run(step(10, until=STEP + SPIKE), 'cpu', target=int(round(rho * 100)), max_replicas=10, timeout=TIMEOUT, retries=5, budget=beta, horizon=hor)
            obs = 'stuck' if stuck(o, hor) else str(bad_until(o, STEP + SPIKE))
            print('  %.1f | %.1f | %.2f | %s | %s' % (rho, beta, a, 'stuck' if pred is None else '%.0f' % pred, obs))


def t17():
    print('T17 CPU signal with a replica ceiling M, 10x spike 300 s then back, 2 retries (amplified load needs 15 pods): M | state | recovery after the spike | recovery x (M - 15)')
    for M in (14, 15, 16, 20, 25, 40):
        hor = 4 * H
        o = run(step(10, until=STEP + SPIKE), 'cpu', dead=DEAD, max_replicas=M, timeout=TIMEOUT, retries=2, horizon=hor)
        trapped = stuck(o, hor)
        t = bad_until(o, STEP + SPIKE)
        print('  %3d | %s | %s | %s' % (M, 'stuck within 16 h' if trapped else 'recovers', '' if trapped else '%d s' % t, '' if trapped else '%d' % (t * (M - 15))))


def t18():
    print('T18 staircase traces for the figure, 10 pods at 50%: overload | (seconds after the step, pods ordered, pods counted ready) at each change')
    for k in (3, 10, 30):
        _, seq = orders(k, 10)
        print('  %3dx | %s' % (k, ' '.join('(%d,%d,%d)' % s for s in seq)))


def t19():
    print('T19 cluster-sized predictions, 4 pods at 50%, ceiling 50: overload | orders (seconds after the step, pods ordered) | time to capacity | peak | pods needed at target')
    for k in (3, 5, 10):
        o, seq = orders(k, 4, max_replicas=50, until=1200)
        print('  %3dx | %s | %d s | %d | %d' % (k, ' '.join('(%d,%d)' % s[:2] for s in seq), to_capacity(o), o['peak'], pods_needed(o, k)))


def t20():
    print('T20 one sync of the ported calculation, pods request 1000m, target 50%, every ready pod at its limit: replicas | ready | not yet ready | ratio over ready pods | utilization over all pods (%) | recommendation')
    for cur, ready, unready in ((16, 10, 6), (20, 10, 10), (40, 10, 30), (40, 20, 20), (40, 40, 0)):
        rec, util = resource_replicas(cur, [1000] * ready, unready, 1000, 50)
        allu = 1000 * ready * 100 // (1000 * (ready + unready))
        print('  %3d | %3d | %3d | %.2f | %3d | %d' % (cur, ready, unready, util / 50, allu, rec))


def t21():
    print('T21 hottest whole-percent target that sizes a k-fold overload within R rounds, limit = request: u* <= k^(-1/(R+1)); simulated time to capacity at that target (R rounds of 120 s, give or take one sync of alignment; never = no scale-up)')
    for k in (3, 10, 30, 100):
        cells = []
        for R in (1, 2, 4, 6, 15):
            t = hottest_target(k, R)
            o = run(step(k), 'cpu', dead=DEAD, target=t, horizon=3600)
            cells.append('R=%d: %d%%, %s' % (R, t, 'never' if o['t_cap'] is None else '%d s' % to_capacity(o)))
        print('  %4dx | %s' % (k, ' | '.join(cells)))


def t22():
    print('T22 saturated reading inside the tolerance band, limit = request, 10 pods all at their limit: target | ratio 100/target | recommendation')
    for t in (80, 85, 89, 90, 91, 93, 95):
        rec, util = resource_replicas(10, [1000] * 10, 0, 1000, t)
        print('  %d%% | %.3f | %d' % (t, util / t, rec))


def t23():
    print('T23 the tolerance band ending a round early, 10x step at a 63% target: (seconds after the step, pods ordered, pods counted ready) at each change, then the hold')
    tr = []
    run(step(10), 'cpu', dead=DEAD, target=63, horizon=1500, trace=tr)
    seq = []
    for t, n, ready, _ in tr:
        if STEP <= t <= STEP + 620 and (not seq or seq[-1][1:] != (n, ready)):
            seq.append((t - STEP, n, ready))
    print('  ' + ' '.join('(%d,%d,%d)' % s for s in seq))
    rec, util = resource_replicas(23, [1000] * 16, 7, 1000, 63)
    print('  at 23 pods with 16 ready: utilization over all pods %d%%, ratio %.3f, recommendation %d' % (1000 * 16 * 100 // (1000 * 23), (1000 * 16 * 100 // (1000 * 23)) / 63, rec))


def t24():
    print('T24 deployed backlog loop, dead 90 s, window 300 s, 200 pods needed: pods every 60 s over the last hour of a 20 h run | standing delay T/c')
    for d in (60, 150):
        tr = []
        backlog(d, trace=tr)
        print('  %3d s | %s' % (d, ' '.join(str(h[0]) for h in tr[-3600::60])))


def t25():
    print('T25 deployed backlog loop, dead 90 s, 200 pods needed, ceiling 2000: T/c | window | pods 5th..95th percentile (mean) | min..max | predicted boundary with 10 s sampling delay')
    for d in (1, 10, 40):
        for w in (300, 0):
            o = backlog(d, window=w)
            pred = 100 / critical_a((w + 10) / 100, hi=400.0)
            print('  %3d s | %3d s | %d..%d (%d) | %d..%d | %.1f s' % (d, w, o['p05'], o['p95'], o['mean'], o['n_lo'], o['n_hi'], pred))


def t26():
    print('T26 idealized backlog loop after an upward step from rest (x = -1), 60 dead times, dt 0.002: a = c*tau/T | w | largest overshoot of x above 0 | steps at which the acting recommendation fell')
    for a in (1 / math.e, 0.40, 0.50):
        for w in (1, 10, 100):
            top, falls = step_response(a, w)
            print('  %.4f | %3d | %.6f | %d' % (a, w, top, falls))


def t27():
    print('T27 idealized backlog loop with no window (w = 0) and a short one, at a = c*tau/T = 8 (standing delay of tau/8): w | a | disturbance decays?')
    for w in (0.0, 0.1):
        print('  %.1f | 8 | %s' % (w, 'decays' if growth(8.0, w) < 1.0 else 'grows'))


def t28():
    print('T28 one sync of the ported external per-pod calculation, threshold 10 messages per pod: replicas (consuming or on order) | backlog | backlog over (threshold x replicas) | recommendation')
    for cur, backlog_msgs in ((100, 2000), (200, 2100), (200, 2300), (300, 4000), (300, 3000), (400, 1000)):
        print('  %3d | %4d | %.3f | %d' % (cur, backlog_msgs, backlog_msgs / (10 * cur), external_per_pod_replicas(cur, backlog_msgs, 10)))


def t29():
    print('T29 sweeps of the ported calculations. (a) CPU, request 1000m, target 50%, ready pods at their limit: ready | recommendation for replicas 10..60')
    for ready in (10, 20):
        recs = [resource_replicas(cur, [1000] * ready, cur - ready, 1000, 50)[0] for cur in range(ready, 61)]
        print('  a %d | %s' % (ready, ' '.join(str(r) for r in recs)))
    print('  (b) external per-pod, threshold 10: replicas | recommendation for backlog 0, 100, ..., 5000')
    for cur in (100, 200, 300):
        print('  b %d | %s' % (cur, ' '.join(str(external_per_pod_replicas(cur, L, 10)) for L in range(0, 5001, 100))))


def t30():
    print('T30 request-level, fixed capacity, NO spike (k = 1), 20000 s, 2 retries, 3 seeds: rho | A*rho | timeouts per seed | stuck at the end')
    for rho in (0.5, 0.8, 0.9, 0.95):
        res = [simulate(rho, 2, s, k=1.0, horizon=20000.0) for s in range(3)]
        print('  %.2f | %.2f | %s | %s' % (rho, 3 * rho, ' '.join(str(n) for _, n in res), ' '.join('yes' if (last_timeout and last_timeout > 19900) else 'no' for last_timeout, _ in res)))


def t31():
    print('T31 cluster-sized trap predictions: fixed 4 pods, fivefold spike 300 s, timeout 10 s, 2 retries (A = 3): rho | A*rho | predicted recovery | fluid model')
    for rho in (0.20, 0.25, 0.30, 0.40):
        a = 3 * rho
        pred = recovery_long_spike(5, rho, 3, SPIKE)
        hor = 20000 if pred is None else int(pred * 1.3) + 3000
        o = run(step(5, until=STEP + SPIKE), 'cpu', target=int(round(rho * 100)), n0=4, max_replicas=4, timeout=TIMEOUT, retries=2, horizon=hor)
        if o['last_bad'] is None:
            obs = 'no timeouts: the spike is no trigger'
        else:
            obs = 'stuck' if stuck(o, hor) else str(bad_until(o, STEP + SPIKE))
        print('  %.2f | %.2f | %s | %s' % (rho, a, 'stuck' if pred is None else '%.0f' % pred, obs))


def t32():
    print('T32 anatomy of the trap, sustained 10x step at a 50% target, timeout 10 s, 2 retries, wasted work; every 30 s from the step: signal | (seconds, pods serving, good requests/s, wasted requests/s)')
    for sig in ('first', 'ingress'):
        se = []
        run(step(10), sig, dead=DEAD, timeout=TIMEOUT, retries=2, horizon=1400, series=se)
        print('  %-7s | %s' % (sig, ' '.join('(%d,%d,%d,%d)' % (t - STEP, serving, round(good), round(wasted))
                                            for (t, serving, _, _, good, wasted, _, _) in se if t >= STEP and (t - STEP) % 30 == 0 and t - STEP <= 1200)))


def t33():
    print('T33 retry amplification of a stack and the threshold 1/A: stack | A | 1/A')
    for name, layers in (('client retries twice', [3]), ('client retries twice, gateway retries twice', [3, 3]), ('client retries twice, gateway retry budget 20%', [3, 1.2])):
        A = 1.0
        for f in layers:
            A *= f
        print('  %s | %.1f | %.1f%%' % (name, A, 100 / A))


def t34():
    print('T34 peak backlog against overload, from the T2 runs: overload | rounds | peak backlog (s of base load) | backlog / (overload x rounds) | local growth exponent from the previous overload')
    prev = None
    for k in (3, 5, 10, 30, 100, 300):
        o = saturated(k)
        R = rounds(k)
        b = o['peak_backlog'] / o['base']
        ex = '' if prev is None else '%.2f' % (math.log(b / prev[1]) / math.log(k / prev[0]))
        print('  %4dx | %d | %d | %.1f | %s' % (k, R, b, b / (k * R), ex))
        prev = (k, b)


def t35():
    print('T35 Pareto overloads (alpha 1.5, 3000 trials), CPU signal, timeout 10 s, 2 retries: admission bound (s of capacity) | p50 / p90 / p99 peak backlog | p50 / p90 / p99 rejected or lost | tail index backlog | tail index lost | p99 time to capacity')
    for b in (None, 60, 20, 5, 2):
        ks, tc, bl, ov, lost = study(1.5, 3000, signal='cpu', dead=DEAD, timeout=TIMEOUT, retries=2, shed_s=b)
        print('  %4s | %.1f / %.1f / %.1f | %.1f / %.1f / %.1f | %.2f | %.2f | %.0f s' % ('none' if b is None else '%d s' % b, q(bl, .5), q(bl, .9), q(bl, .99), q(lost, .5), q(lost, .9), q(lost, .99), tail_index(bl), tail_index(lost), q(tc, .99)))


def t36():
    print('T36 cluster-sized predictions for Part 4, 4 pods at 50%, 2 retries, timeout 10 s. (a) sustained 5x step, ceiling 50: admission bound | peak pods | demand lost')
    for shed in (None, 5):
        o = run(step(5), 'cpu', dead=DEAD, n0=4, max_replicas=50, timeout=TIMEOUT, retries=2, shed_s=shed, horizon=7200)
        print('  a %s | %d | %.1f%%' % ('none' if shed is None else '%d s' % shed, o['peak'], 100 * o['lost'] / o['first']))
    print('  (b) 5x spike for 300 s then back, CPU signal, replica ceiling M (amplified load after the spike needs 6 pods): M | recovery after the spike')
    for M in (5, 6, 7, 8, 12):
        hor = 40000
        o = run(step(5, until=STEP + SPIKE), 'cpu', dead=DEAD, n0=4, max_replicas=M, timeout=TIMEOUT, retries=2, horizon=hor)
        print('  b %d | %s' % (M, 'stuck' if stuck(o, hor) else '%d s' % bad_until(o, STEP + SPIKE)))


def t37():
    print('T37 approximations to Phi(w). (a) harmonic balance, closed form for w >= 1, against the computed curve: w | closed form | computed | error')
    for w in (1.0, 2.0, 3.33, 5.0, 10.0):
        c = phi(w)
        print('  a %.2f | %.3f | %.3f | %+.1f%%' % (w, phi_harmonic_balance(w), c, 100 * (phi_harmonic_balance(w) / c - 1)))
    long_phi = {}
    for w in (100.0, 400.0):
        long_phi[w] = 1.0 / critical_a(w, lo=0.3, hi=1.0, cycles_time=3000.0)
    print('  (b) long windows, 3000 dead times of integration: w | computed Phi: ' + ' | '.join('%.0f: %.3f' % (w, v) for w, v in long_phi.items()))
    pts = [(w, phi(w)) for w in (10.0, 20.0, 40.0)] + list(long_phi.items())
    best = None
    for c10 in range(50, 600):
        cc = c10 / 10
        for w0x in range(1, 100):
            w0 = w0x / 100
            err = max(abs(math.e / (1 + cc / math.log(w / w0) ** 2) / v - 1) for w, v in pts)
            if best is None or err < best[0]:
                best = (err, cc, w0)
    err, cc, w0 = best
    print('  (c) asymptotic form e/(1 + c/ln^2(w/w0)) fitted on w = 10..400: c = %.1f, w0 = %.2f, largest error %.2f%%' % (cc, w0, 100 * err))
    for w in (2.0, 3.33, 5.0):
        v = phi(w)
        print('      w %.2f: form %.3f, computed %.3f, error %+.1f%%' % (w, math.e / (1 + cc / math.log(w / w0) ** 2), v, 100 * (math.e / (1 + cc / math.log(w / w0) ** 2) / v - 1)))
    print('  (d) dominant root of s + a e^{-s} = 0 at a = (1+delta)/e, against -1 +/- i sqrt(2 delta): delta | root | approximation')
    for d in (0.02, 0.05, 0.1):
        a = (1 + d) / math.e
        s = complex(-1, math.sqrt(2 * d))
        for _ in range(60):
            s = s - (s + a * cmath.exp(-s)) / (1 - a * cmath.exp(-s))
        print('      %.2f | %.4f%+.4fi | -1.0000%+.4fi' % (d, s.real, s.imag, math.sqrt(2 * d)))


def t38():
    print('T38 server farms with setup times (Gandhi, Harchol-Balter and Adan 2010): exact mean response time against the request-level simulator, 300,000 jobs, 3 seeds; time unit = mean job size')
    for lam, mu, alpha, k in ((8.0, 1.0, 1.0, 10), (5.0, 1.0, 0.2, 10), (8.0, 1.0, 0.1, 10)):
        ex = 1 / alpha + erlang_c_mean_response(lam, mu, k)
        sims = [setup_simulate(lam, mu, alpha, k, True, s) for s in range(3)]
        print('  staggered, k=%d, load %.1f, mean setup %.0f | exact %.3f | simulated %s' % (k, lam / mu, 1 / alpha, ex, ' '.join('%.3f' % x for x in sims)))
    for lam, mu, alpha in ((8.0, 1.0, 1.0), (8.0, 1.0, 0.1), (20.0, 1.0, 0.05)):
        ex = onoff_inf_mean_response(lam, mu, alpha)
        sims = [setup_simulate(lam, mu, alpha, None, False, s) for s in range(3)]
        print('  on/off, unlimited servers, load %.0f, mean setup %.0f | exact %.3f | simulated %s' % (lam / mu, 1 / alpha, ex, ' '.join('%.3f' % x for x in sims)))


def t39():
    print('T39 cluster-sized predictions for Part 2: queue consumer, 10 msg/s per pod, step 50 -> 200 msg/s (5 -> 20 pods needed), dead 90 s, ceiling 100, last hour of a 20 h run: T/c | window | pods 5th..95th percentile (mean) | min..max')
    for d, w in ((60, 300), (150, 300), (60, 60), (1, 300), (1, 0)):
        o = backlog_run(round(d * 10.0), lam0=50.0, lam1=200.0, c=10.0, dead=DEAD, window=w, horizon=72000, step_at=600, n_max=100)
        print('  %3d s | %3d s | %d..%d (%.1f) | %d..%d' % (d, w, o['p05'], o['p95'], o['mean'], o['n_lo'], o['n_hi']))


def t40():
    print('T40 cluster-sized predictions for Part 3, 4 pods at a 50% target, sustained 5x step, ceiling 50, timeout 10 s, 2 retries: signal | peak pods | pods at the end | demand lost | recovery after the step')
    for sig in ('first', 'ingress', 'pair'):
        o = run(step(5), sig, dead=DEAD, n0=4, max_replicas=50, timeout=TIMEOUT, retries=2, horizon=7200)
        print('  %-7s | %d | %d | %.1f%% | %s' % (sig, o['peak'], o['final'], 100 * o['lost'] / o['first'], 'stuck' if stuck(o, 7200) else '%d s' % bad_until(o, STEP)))
    o = run(step(1), 'pair', dead=DEAD, n0=4, max_replicas=50, timeout=TIMEOUT, retries=2, horizon=3600)
    print('  pair, no step | pods at the end %d' % o['final'])


def t41():
    print('T41 cluster-sized predictions for Part 4 F3, 4 pods at 50%, sustained 5x step, CPU signal, ceiling 50, timeout 10 s, 2 retries: admission bound | peak pods | demand lost | abandoned work served (s of base load)')
    for shed in (20, 5):
        o = run(step(5), 'cpu', dead=DEAD, n0=4, max_replicas=50, timeout=TIMEOUT, retries=2, shed_s=shed, horizon=7200)
        print('  %d s | %d | %.1f%% | %.0f' % (shed, o['peak'], 100 * o['lost'] / o['first'], o['wasted'] / o['base']))


def t42():
    print('T42 cluster-sized prediction for Part 1 F3, 4 pods at 50%, sustained 5x step, CPU limit 4x the request (1000m over 250m), ceiling 50: peak pods | pods needed at the target | seconds from the step until serving capacity meets the load')
    o = run(step(5), 'cpu', dead=DEAD, n0=4, max_replicas=50, limit=4.0, horizon=7200)
    print('  %d | %d | %d s' % (o['peak'], pods_needed(o, 5), to_capacity(o)))


def t43():
    print('T43 the same sweep as T35 either side of the 10 s timeout (alpha 1.5, 3000 trials, CPU signal, 2 retries): admission bound (s of capacity) | p50 / p90 / p99 peak backlog | p50 / p90 / p99 rejected or lost | tail index backlog | tail index lost | p99 time to capacity')
    for b in (12, 8):
        ks, tc, bl, ov, lost = study(1.5, 3000, signal='cpu', dead=DEAD, timeout=TIMEOUT, retries=2, shed_s=b)
        print('  %4s | %.1f / %.1f / %.1f | %.1f / %.1f / %.1f | %.2f | %.2f | %.0f s' % ('%d s' % b, q(bl, .5), q(bl, .9), q(bl, .99), q(lost, .5), q(lost, .9), q(lost, .99), tail_index(bl), tail_index(lost), q(tc, .99)))


def t44():
    print('T44 the T39 predictions for the last hour of a 5 h run, the length of the cluster suite\'s queue runs: T/c | window | pods 5th..95th percentile (mean) | min..max')
    for d, w in ((60, 300), (150, 300), (60, 60), (1, 300), (1, 0)):
        o = backlog_run(round(d * 10.0), lam0=50.0, lam1=200.0, c=10.0, dead=DEAD, window=w, horizon=18000, step_at=600, n_max=100)
        print('  %3d s | %3d s | %d..%d (%.1f) | %d..%d' % (d, w, o['p05'], o['p95'], o['mean'], o['n_lo'], o['n_hi']))


def t45():
    print('T45 recovery after a spike, Proposition 7: leading term D(Akp-1)/(1-Ap) and the piecewise form (Akp-1)(D-t0)/(1-Ap) + tau_out/(1-p), t0 = tau_out/(kp-1), against the fluid model; timeout 10 s, spike 300 s: case | k | rho | A | leading | piecewise | fluid')
    for label, k, rho, retries, beta, n0 in (('retries', 10, 0.5, 0, None, 10), ('retries', 10, 0.25, 1, None, 10), ('retries', 10, 0.3, 1, None, 10),
                                             ('retries', 10, 0.2, 2, None, 10), ('retries', 10, 0.4, 1, None, 10), ('budget', 10, 0.5, 5, 0.1, 10),
                                             ('budget', 10, 0.5, 5, 0.2, 10), ('budget', 10, 0.5, 5, 0.5, 10), ('budget', 10, 0.8, 5, 0.1, 10),
                                             ('budget', 10, 0.8, 5, 0.2, 10), ('kit', 5, 0.25, 2, None, 4), ('kit', 5, 0.3, 2, None, 4)):
        a_mult = (1 + beta) if beta is not None else retries + 1
        lead = recovery_long_spike(k, rho, a_mult, SPIKE)
        piece = recovery_piecewise(k, rho, a_mult, SPIKE, TIMEOUT)
        hor = int(lead * 1.3) + 3000
        o = run(step(k, until=STEP + SPIKE), 'cpu', target=int(round(rho * 100)), n0=n0, max_replicas=n0, timeout=TIMEOUT, retries=retries, budget=beta, horizon=hor)
        print('  %-7s | %2d | %.2f | %.1f | %.0f | %.0f | %d' % (label, k, rho, a_mult, lead, piece, bad_until(o, STEP + SPIKE)))


def t46():
    print('T46 peak pods after a step: round arithmetic (double every round while the metric is saturated, i.e. while ready capacity is below demand or a backlog remains) against the simulated peak; 10 pods at 50%, limit = request: overload | round model | simulated')
    # Work in pods at full rate: the step brings k n0 u of it, and n0 2^m saturated pods serve
    # as many each round; the backlog is the work left over, in pod-rounds.
    n0, u = 10, 0.5
    for k in (3, 5, 10, 30, 100, 300):
        demand, backlog, m, model = k * n0 * u, 0.0, 0, n0
        while n0 * 2 ** m < demand or backlog > 0:
            model = 2 * n0 * 2 ** m
            backlog = max(0.0, backlog + demand - n0 * 2 ** m)
            m += 1
        print('  %4dx | %d | %d' % (k, model, saturated(k)['peak']))



def t47():
    print('T47 one step of the cluster-sized queue consumer, worked through: 10 msg/s per pod, demand 50 -> 200 msg/s (5 -> 20 pods needed), dead 90 s, window 300 s, ceiling 100, threshold 10 messages per pod (standing delay 1 s); every 30 s from the step: seconds | pods ordered | pods consuming | backlog (messages)')
    tr = []
    backlog_run(10, lam0=50.0, lam1=200.0, c=10.0, dead=DEAD, window=300, horizon=600 + 1200, step_at=600, n_max=100, trace=tr)
    for s in range(0, 1200, 30):
        ordered, consuming, queued = tr[600 + s]
        print('  %4d | %3d | %3d | %d' % (s, ordered, consuming, round(queued)))


def t48():
    print('T48 every signal and lever of Parts 3 and 4 on common axes, sustained 10x step, 10 pods before it, timeout 10 s, the first hour after the step: configuration | signal | target | retry policy | mean pods held over pods that carry the stepped demand at full rate | first attempts lost (s of the stepped demand) | state at the end of the hour')
    hour = STEP + 3600
    for name, sig, target, kw in (('cpu', 'cpu', 50, dict(retries=2)), ('ingress', 'ingress', 50, dict(retries=2)),
                                  ('pair', 'pair', 50, dict(retries=2)), ('first', 'first', 50, dict(retries=2)),
                                  ('first, target 30%', 'first', 30, dict(retries=2)), ('first, target 25%', 'first', 25, dict(retries=2)),
                                  ('first, budget 20%', 'first', 50, dict(retries=5, budget=0.2)), ('first, budget 50%', 'first', 50, dict(retries=5, budget=0.5)),
                                  ('first, bound 5 s', 'first', 50, dict(retries=2, shed_s=5)), ('cpu, bound 5 s', 'cpu', 50, dict(retries=2, shed_s=5))):
        o = run(step(10), sig, dead=DEAD, target=target, timeout=TIMEOUT, horizon=hour, **kw)
        full_rate = stepped(o, 10) / RATE
        held = (o['pod_s'] - STEP * 10) / (hour - STEP)
        policy = ('budget %d%%' % round(100 * kw['budget'])) if 'budget' in kw else ('2 retries, bound %d s' % kw['shed_s'] if 'shed_s' in kw else '2 retries')
        print('  %-18s | %-7s | %d%% | %-20s | %.2f | %.0f s | %s' % (name, sig, target, policy, held / full_rate, o['lost'] / stepped(o, 10),
                                                                   'failed' if stuck(o, hour) else 'healthy'))


def t49():
    print('T49 how sure the tail indices are: Hill estimates over 3,000 Pareto overloads (alpha 1.5, CPU signal) with a 90% bootstrap interval (400 resamples, seed 11), as the share of the sample treated as the tail varies: quantity | share | estimate | 5th..95th percentile of the bootstrap')
    ks, _, backlog_s, _, _ = study(1.5, 3000, signal='cpu', dead=DEAD)
    _, _, _, _, lost_s = study(1.5, 3000, signal='cpu', dead=DEAD, timeout=TIMEOUT, retries=2, shed_s=5)
    rng = random.Random(11)
    draws = [[rng.randrange(3000) for _ in range(3000)] for _ in range(400)]
    for label, sample in (('K, the overload', ks), ('peak backlog, no bound', backlog_s), ('refused or lost, bound 5 s', lost_s)):
        for share in (0.02, 0.05, 0.1, 0.2, 0.3):
            boot = sorted(tail_index([sample[i] for i in d], share) for d in draws)
            print('  %-26s | %.2f | %.2f | %.2f..%.2f' % (label, share, tail_index(sample, share), q(boot, .05), q(boot, .95)))

if __name__ == '__main__':
    sys.exit(harness.main(sys.argv[1:], HERE, harness.collect(globals())))
