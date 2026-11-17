"""Sections of Part 1, a shared signal: T1, T2, T3, T4, T5, T19, T20, T21, T22, T23, T24, T39, T78, T90, T91, T92, T103, T107, T113, T118, T119."""
import math

from formulas import (coupled_relative_gain, custom_metric_relative_gain, directional_band, doubling_bracket,
                      elasticity, equilibrium_band, relative_gain_array, resting_margin, same_metric_gain,
                      split_metric_gain, step_factor, step_interval, stopping_scale_up_tolerance,
                      vpa_utilisation)
from gc_data import CYCLE_LBO, pair_elasticities, peak_elasticity
from hpa_vpa import simulate
from relist import simulate_limited as relist_limited


TARGETS = (0.5, 0.6, 0.7, 0.8, 0.9)


QS = (1.0, 1.1, 1.2, 1.3, 1.4, 1.5)


def gain(x):
    return 'singular' if x is None else '%.3f' % x


def t1():
    print('T1 relative gain of the horizontal loop: shared metric, recommended split, split with coupling')
    rga = relative_gain_array(same_metric_gain())
    print('  shared CPU metric | %s' % gain(None if rga is None else rga[0][0]))
    print('  CPU and memory, no coupling | %s' % gain(relative_gain_array(split_metric_gain(0.0, 1.0))[0][0]))
    for beta in (0.1, 0.3, 0.5, 0.9, 1.0, 2.0):
        for theta in (0.5, 1.0):
            print('  CPU and memory, beta %.1f theta %.1f | beta theta %.2f | %s'
                  % (beta, theta, beta * theta, gain(coupled_relative_gain(beta, theta))))


def t2():
    print('T2 horizontal targets with an equilibrium (margin 0.15, tolerance 0.1; vertical tolerance 0 for a '
          'steady load, 0.1 the documented threshold): q | vertical utilisation | band, vertical tolerance 0 | '
          'common targets inside | band, vertical tolerance 0.1 | common targets inside')
    for q in QS:
        row = []
        for vtol in (0.0, 0.1):
            lo, hi = equilibrium_band(q=q, vtol=vtol)
            inside = [t for t in TARGETS if lo <= t <= hi]
            row.append('%.3f to %.3f | %s' % (lo, hi, ', '.join('%.1f' % t for t in inside) or 'none'))
        print('  %.1f | %.3f | %s' % (q, vpa_utilisation(q=q), ' | '.join(row)))


def t3():
    print('T3 drift below the band (target 0.5, steady demand 100 cores, 10 replicas, documented recommender: '
          '90th percentile, margin 0.15, half-life 24 h, floor 25 millicores): hour | replicas | request | '
          'utilisation | requested cores')
    samples, _ = simulate(0.5, sample_h=12)
    for hour, n, r, u, total in samples:
        print('  %d | %d | %.3f | %.3f | %.1f' % (round(hour), n, r, u, total))


def t4():
    print('T4 long-run replica doubling time below the band, steady demand (400 days): target | step factor | fastest h | simulated h | slowest h | replicas at the end')
    for t in TARGETS + (0.75, 0.78):
        b = doubling_bracket(t)
        samples, sim = simulate(t, days=400)
        fast = '-' if b is None else '%.1f' % b[0]
        slow = '-' if b is None else ('unbounded' if b[1] == float('inf') else '%.1f' % b[1])
        print('  %.2f | %.3f | %s | %s | %s | %d' % (t, step_factor(t), fast, '-' if sim is None else '%.1f' % sim, slow, samples[-1][1]))


def t5():
    print('T5 coupling from published garbage-collection cost (heap multiple 2, 3, 5: slowdown 1.70, 1.17, 1.00): heap range | beta | gain at theta 0.5 | gain at theta 1.0')
    for (h1, s1), (h2, s2) in (((2, 1.70), (3, 1.17)), ((3, 1.17), (5, 1.00))):
        beta = elasticity(h1, s1, h2, s2)
        print('  %dx to %dx | %.2f | %s | %s' % (h1, h2, beta, gain(coupled_relative_gain(beta, 0.5)),
                                                gain(coupled_relative_gain(beta, 1.0))))


def t19():
    print('T19 horizontal loop on a custom metric, vertical loop on CPU: gamma (service rate against CPU request) | relative gain of the horizontal loop')
    for gamma in (0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0):
        print('  %.2f | %s' % (gamma, gain(custom_metric_relative_gain(gamma))))


def t20():
    print('T20 vertical margin at which a shared-metric pairing rests (tolerance 0.1; vertical tolerance 0 and '
          '0.1): horizontal target | margin at q 1.0, vtol 0 | margin at q 1.0, vtol 0.1 | margin at q 1.2, '
          'vtol 0 | request over mean usage, vtol 0 | request over mean usage, vtol 0.1')
    for u_h in TARGETS:
        a, b = resting_margin(u_h, 1.0)
        a1, b1 = resting_margin(u_h, 1.0, vtol=0.1)
        c, d = resting_margin(u_h, 1.2)
        print('  %.1f | %.2f to %.2f | %.2f to %.2f | %.2f to %.2f | %.2f to %.2f | %.2f to %.2f' % (
            u_h, a, b, a1, b1, c, d, 1 / (u_h * 1.1), 1 / (u_h * 0.9), 1 / (u_h * 1.1 * 1.1), 1 / (u_h * 0.9 * 0.9)))


def t21():
    print('T21 long-run replica doubling under the documented vertical update rule (200 days): target | bracket h | instant h | bounds closed h | age-and-threshold only h')
    def f(x):
        return '-' if x is None else '%.1f' % x
    for t in (0.5, 0.6, 0.7):
        b = doubling_bracket(t)
        print('  %.1f | %.1f to %.1f | %s | %s | %s' % (t, b[0], b[1], f(simulate(t, days=200)[1]),
              f(simulate(t, days=200, updates='documented', bound=0.0)[1]), f(simulate(t, days=200, updates='documented', bound=None)[1])))


def t22():
    print('T22 targets near the band at q 1.0 (narrow band from %.3f, widened from %.3f), 200 days: target | '
          'instant: replicas, doubling h | bounds closed: replicas, doubling h | age-and-threshold only: '
          'replicas, doubling h' % (
        equilibrium_band()[0], equilibrium_band(vtol=0.1)[0]))
    def f(x):
        return 'none' if x is None else '%.1f' % x
    for t in (0.70, 0.72, 0.75, 0.78):
        rows = [simulate(t, days=200, **kw) for kw in ({}, dict(updates='documented', bound=0.0), dict(updates='documented', bound=None))]
        print('  %.2f | %s' % (t, ' | '.join('%d, %s' % (r[0][-1][1], f(r[1])) for r in rows)))


def t23():
    print('T23 the drift as a staircase (target 0.5 and 0.6, steady demand): step interval h, theory | target | step at h | gap h | replicas before | after | factor')
    print('  %.2f h = 24 x log2(1 / (1 - 0.9))' % step_interval())
    for t in (0.5, 0.6):
        samples, _ = simulate(t, days=40, sample_h=0.25)
        steps, last = [], None
        for hour, n, r, u, total in samples:
            if last is not None and n > last[1] * 1.2:
                steps.append((hour, last[1], n))
            last = (hour, n)
        for (h0, a0, b0), (h1, a1, b1) in zip(steps, steps[1:]):
            print('  %.1f | %.1f | %.1f | %d | %d | %.3f' % (t, h1, h1 - h0, a1, b1, b1 / a1))
    print('  daily cycle, target 0.5, 120 days: amplitude | doubling h')
    for amp in (0.0, 0.1, 0.2, 0.3, 0.45, 0.6):
        print('  %.2f | %.1f' % (amp, simulate(0.5, amplitude=amp, days=120)[1]))


SETTINGS = ((), (('percentile', 0.5),), (('percentile', 0.95),), (('half_life', 12.0),), (('half_life', 48.0),),
            (('margin', 0.0),), (('margin', 0.3),))


def t24():
    print('T24 the staircase law at other recommender settings (target 0.5, steady demand, request floor '
          'lowered to 0.001 cores so each staircase runs long enough to measure, warm-up 2.5 step intervals, '
          '300 days): setting | step h | factor | fastest h | simulated h | slowest h')
    for setting in SETTINGS:
        kw = dict(setting)
        p, h, m = kw.get('percentile', 0.9), kw.get('half_life', 24.0), kw.get('margin', 0.15)
        b = doubling_bracket(0.5, margin=m, half_life=h, percentile=p)
        _, sim = simulate(0.5, days=300, request_floor=0.001, warmup_h=2.5 * step_interval(h, p), **kw)
        name = ', '.join('%s %s' % (k.replace('_', '-'), v) for k, v in setting) or 'documented defaults'
        print('  %s | %.1f | %.3f | %.1f | %s | %.1f' % (name, step_interval(h, p), step_factor(0.5, m), b[0], '-' if sim is None else '%.1f' % sim, b[1]))


def t39():
    print('T39 coupling from current collectors (OpenJDK 17, cycle lower-bound overheads, geometric mean of 16 '
          'benchmarks, ISPASS 2022; heap as a multiple of the minimum; beta from neighboring two-decimal '
          'table values): collector | steepest heap range | beta | gain at theta 1.0 | gain at theta 0.5 | '
          'beta, 5.2x to 6.0x | gain at theta 1.0')
    for gc in CYCLE_LBO:
        a, b, beta = peak_elasticity(gc)
        last = pair_elasticities(gc)[-1][2]
        print('  %s | %.1fx to %.1fx | %.2f | %s | %s | %.2f | %s' % (gc, a, b, beta, gain(coupled_relative_gain(beta, 1.0)),
                                                         gain(coupled_relative_gain(beta, 0.5)), last, gain(coupled_relative_gain(last, 1.0))))


def t78():
    print('T78 a scale-up tolerance per direction (HPAConfigurableTolerance, GA in Kubernetes 1.37) on the '
          'drifting pairing, margin 0.15, scale-down tolerance 0.1, steady load: target | scale-up tolerance '
          "that stops the staircase, step factor - 1 | the same with the histogram's 5% buckets, step factor / "
          '1.05 - 1 | lowest simulated tolerance, in steps of 0.01, at which replicas stay below 1.5 x the '
          'start over 60 days | utilisation at which the horizontal loop then first scales up, target x (1 + '
          'tolerance) | low edge of the band at that tolerance')
    for u_h in (0.5, 0.6, 0.7):
        stop = stopping_scale_up_tolerance(u_h)
        bucketed = step_factor(u_h, bucket=1.05) - 1
        found = None
        for i in range(0, 100):
            t = round(0.01 * i, 2)
            s = simulate(u_h, days=60, tol_up=t)[0]
            if s[-1][1] < 1.5 * s[0][1]:
                found = t
                break
        print('  %.1f | %.3f | %.3f | %.2f | %.3f | %.3f' % (u_h, stop, bucketed, found, u_h * (1 + stop), directional_band(tol_up=stop)[0]))


def t90():
    from formulas import lognormal_q, pareto_q, regime, regime_boundaries
    print("T90 the paired loops over the tail weight of per-pod usage: each pod's samples are the mean times a "
          'lognormal factor of mean one and shape sigma, the horizontal loop holds the mean, the vertical loop '
          'sizes from the 90th percentile; margin 0.15, tolerance 0.1. Rows "edges": target | sigma at which '
          'the regime changes, closed form. Rows "regime": target | sigma | q = exp(1.2816 sigma - sigma^2/2) '
          '| regime by the band | replicas after 30 days from 10, simulated (seed 1, 20 samples a minute, '
          'request floor lowered to 1e-6 cores). Rows "floor": sigma | replicas after 60 days at the documented '
          'floor of 25 millicores. Rows "pareto": tail index | q for a Pareto factor of mean one | regime at '
          'target 0.5')
    for u_h in (0.5, 0.6, 0.7):
        print('  edges | %.1f | %s' % (u_h, ', '.join('%.4f' % x for x in regime_boundaries(u_h))))
    for sigma in (0.0, 0.3, 0.55, 0.7, 0.9, 1.2, 1.6, 2.0, 2.4):
        q = lognormal_q(sigma)
        s = simulate(0.5, days=30, noise_sigma=sigma, request_floor=1e-6)[0]
        print('  regime | 0.5 | %.2f | %.4f | %s | %d' % (sigma, q, regime(0.5, q), s[-1][1]))
    for sigma in (0.0, 2.4):
        print('  floor | %.1f | %d' % (sigma, simulate(0.5, days=60, noise_sigma=sigma)[0][-1][1]))
    for alpha in (1.2, 1.5, 2.0, 3.0, 5.0):
        q = pareto_q(alpha)
        print('  pareto | %.1f | %.4f | %s' % (alpha, q, regime(0.5, q)))


def t91():
    print('T91 an autonomic supervisor on the paired loops: every T hours it estimates q as the vertical '
          "loop's histogram percentile over its mean and sets the margin to max(0, 1 / (0.5 q) - 1); target "
          '0.5, 60 days, replicas from 10, request floor lowered to 1e-6 cores: sigma | T, hours, or none | '
          'replicas at days 5, 30 and 60')
    for sigma in (0.0, 0.3, 1.2, 2.4):
        for period in (None, 1, 24, 96):
            s = [x[1] for x in simulate(0.5, days=60, noise_sigma=sigma, request_floor=1e-6, supervisor_h=period, sample_h=24)[0]]
            print('  %.1f | %s | %d | %d | %d' % (sigma, 'none' if period is None else str(period), s[5], s[30], s[60]))


def t92():
    from formulas import drift_rate, lognormal_q, max_resting_target
    print('T92 the transition at the band\'s edge and the frontier over the tail. Rows "rate": target | drift '
          'rate, per hour, ln F / s* (0 inside the band) | doubling time, hours. Rows "frontier": lognormal '
          'shape sigma | q | highest target that rests at some margin of at least zero, 1 / (q (1 - tol)) | '
          "margin that rests a 50% target at the band's center, 1 / (0.5 q) - 1")
    for u_h in (0.5, 0.6, 0.7, 0.75, 0.78, 0.79, 0.7905, 0.791, 0.8):
        r = drift_rate(u_h)
        print('  rate | %.4f | %.6f | %s' % (u_h, r, '%.1f' % (math.log(2) / r) if r else 'none'))
    for sigma in (0.0, 0.5, 1.0, 1.2816, 1.5, 2.0, 2.5):
        q = lognormal_q(sigma)
        print('  frontier | %.4f | %.4f | %.4f | %.4f' % (sigma, q, max_resting_target(q), 1.0 / (0.5 * q) - 1.0))


def t103():
    print('T103 hidden memory: runs that share the state the dashboards show and differ in what a mechanism '
          'remembers. Rows "histogram": the Part 1 pair at a 0.5 target from 10 replicas, the same requests '
          "and demand, the vertical loop's histogram also holding 200 samples at a multiple of the starting "
          'usage some hours before the start: multiple | hours before | replicas at days 1, 5, 10, 20, 30. '
          'Rows "steps": the same runs: multiple | hours before | first four scaling steps, hour and replicas '
          '| long-run doubling, hours | replicas at day 30 over day 1. Rows "backoff": the Part 3 server with '
          "its wait limit, a sudden full trigger, every client's backoff starting fresh or at its cap: start | "
          'list cost | seeds 1 to 8 still storming in hour 8 | re-watches answered 410 in hour 8, seed 1')
    for prior in ((), ((2.0, 6.0, 200),), ((0.5, 6.0, 200),), ((2.0, 48.0, 200),)):
        days = simulate(0.5, days=30, prior=prior)[0]
        label = 'none | -' if not prior else '%.1f | %.0f' % (prior[0][0], prior[0][1])
        print('  histogram | %s | %s' % (label, ', '.join(str(x[1]) for x in days if x[0] in (24, 120, 240, 480, 720))))
    for prior in ((), ((2.0, 6.0, 200),), ((0.5, 6.0, 200),)):
        days, doubling, jumps = simulate(0.5, days=30, prior=prior, return_jumps=True)
        at = {x[0]: x[1] for x in days}
        label = 'none | -' if not prior else '%.1f | %.0f' % (prior[0][0], prior[0][1])
        print('  steps | %s | %s | %.1f | %.0f' % (label, ', '.join('%.1f h: %d' % j for j in jumps[:4]), doubling, at[720] / at[24]))
    for raised in (False, True):
        for cost in (113.0, 114.0):
            runs = [relist_limited(cost, seed=sd, backoff_raised=raised)[6]['gone_per_hour'][-1] for sd in range(1, 9)]
            print('  backoff | %s | %.0f | %d | %d' % ('raised' if raised else 'fresh', cost, sum(1 for x in runs if x > 0), runs[0]))


def t107():
    from formulas import first_step_delay, prior_weight
    print("T107 Part 1's history statistic: the remembered weight sets when the percentile lets go, and inside "
          'the band it selects where the pair rests. Rows "first": the pair at a 0.5 target, the histogram '
          'also holding a burst: multiple | hours before | samples | remembered weight, start units | first '
          'scale-up, closed form h log2(1 + ln2 (A0/(1-p) - H0)/(r h)), hours | first scale-up, simulated, '
          'hours. Rows "rest": the pair at a 0.8 target, inside the band, 20 days: multiple | hours before | '
          'samples | replicas at day 20 | replicas unchanged over the last five days')
    for prior in ((2.0, 6.0, 200), (2.0, 6.0, 2000), (1.5, 24.0, 1000)):
        w = prior_weight((prior,))
        _, _, jumps = simulate(0.5, days=6, prior=(prior,), return_jumps=True)
        print('  first | %.1f | %.0f | %d | %.1f | %.1f | %.1f' % (prior[0], prior[1], prior[2], w, first_step_delay(w, w), jumps[0][0]))
    for prior in ((1.0, 0.0, 0), (2.0, 6.0, 200), (1.5, 24.0, 1000)):
        samples = simulate(0.8, days=20, prior=((prior,) if prior[2] else ()))[0]
        print('  rest | %.1f | %.0f | %d | %d | %s' % (prior[0], prior[1], prior[2], samples[-1][1], 'yes' if samples[-1][1] == samples[-6][1] else 'no'))


def t113():
    from formulas import pod_mean_cv, spike_share
    print('T113 the scope of the tail regimes (T90): per-pod samples the mean times a lognormal factor of mean '
          'one and shape sigma. Rows "scope": sigma | coefficient of variation of the horizontal loop\'s '
          'reading, the mean of n pods, at n = 3, 10, 100, 1000 | pods at which it falls to the tolerance 0.1, '
          'ceil((exp(sigma^2) - 1) / 0.01) | share of the mean usage carried by samples above 8 and 4 times '
          'the mean')
    for sigma in (0.3, 0.55, 1.2, 1.85, 2.0, 2.4):
        print('  scope | %.2f | %s | %d | %.4f | %.4f' % (sigma, ', '.join('%.3f' % pod_mean_cv(sigma, n) for n in (3, 10, 100, 1000)),
                                                       math.ceil((math.exp(sigma * sigma) - 1.0) / 0.01 - 1e-9), spike_share(sigma, 8.0), spike_share(sigma, 4.0)))


def t118():
    from formulas import critical_xi, split_relative_gain
    from gc_data import CYCLE_LBO, peak_elasticity
    print('T118 the split pairing with the heap structure explicit (Proposition 6), theta = 1: memory the '
          'vertical loop observes follows per-pod load. Columns: source | beta | relative gain with a live set '
          'that does not follow load and a heap that does not grow with its limit (theta_live = 0, xi = 0) | '
          'with the live set following load (theta_live = 1, xi = 0) | the critical xi, where a live set that '
          'follows load and a heap that grows into its limit make the pairing singular | relative gain at xi = '
          '0.3 and 0.6 with theta_live = 1')
    rows = [('Hertz-Berger 2x to 3x', 0.92), ('Hertz-Berger 3x to 5x', 0.31)] + [(gc, peak_elasticity(gc)[2]) for gc in CYCLE_LBO]
    for label, beta in rows:
        print('  %s | %.2f | %s | %s | %.3f | %s | %s' % (label, beta, gain(split_relative_gain(beta, 1.0)), gain(split_relative_gain(beta, 1.0, 1.0)),
                                                       critical_xi(beta, 1.0, 1.0), gain(split_relative_gain(beta, 1.0, 1.0, 0.3)), gain(split_relative_gain(beta, 1.0, 1.0, 0.6))))


def t119():
    print('T119 the signal seam in transit (Part 1): the paired loops drifting at a 0.5 target from 10 '
          'replicas, demand 100 cores steady, a fix applied at an hour of the drift, run to day 40. Columns: '
          'fix | hour applied | replicas then | requested cores then | lowest replicas after | replicas at day '
          '40 | requested cores at day 40 | utilization at day 40 | scaling actions after the fix')
    for hour in (100.0, 400.0, 700.0):
        for label, change in (('none', None), ('target 0.8', {'target': 0.8}), ('scale-up tolerance 0.739', {'tol_up': 0.739})):
            samples, _, jumps = simulate(0.5, days=40, return_jumps=True, sample_h=1.0, change=None if change is None else (hour, change))
            then = [x for x in samples if x[0] <= hour][-1]
            after = [x for x in samples if x[0] > hour]
            print('  %s | %.0f | %d | %.1f | %d | %d | %.1f | %.3f | %d' % (label, hour, then[1], then[4], min(x[1] for x in after), after[-1][1], after[-1][4], after[-1][3], sum(1 for j in jumps if j[0] > hour)))


def t120():
    from formulas_signal import off_heap_gain, singular_heap_share
    print('T120 the split pairing with a live set that does not follow load: only memory outside the heap follows '
          'load, so theta is at most one minus the heap\'s share of observed memory. collector | beta | heap share '
          'below which the pairing is singular (none when beta is at most 1) | gain with the heap at 3/4 of memory | '
          'at 1/2 | at 1/4. Rows "curve": collector | heap share | gain, at the largest theta the share allows, the '
          'heap shares 0 to 0.95 in steps of 0.05')
    sources = [('Hertz-Berger 2x to 3x', 0.92), ('Hertz-Berger 3x to 5x', 0.31)]
    sources += [(gc, peak_elasticity(gc)[2]) for gc in CYCLE_LBO]
    for name, beta in sources:
        share = singular_heap_share(beta)
        print('  %s | %.2f | %s | %s | %s | %s' % (name, beta, 'none' if share is None else '%.3f' % share,
                                                   gain(off_heap_gain(beta, 0.75)), gain(off_heap_gain(beta, 0.5)),
                                                   gain(off_heap_gain(beta, 0.25))))
    for name, beta in sources:
        for k in range(20):
            print('  curve | %s | %.2f | %s' % (name, k / 20, gain(off_heap_gain(beta, k / 20))))
