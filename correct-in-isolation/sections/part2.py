"""Sections of Part 2, a shared time scale: T6, T7, T8, T9, T25, T26, T27, T28, T29, T30, T31, T32, T33, T34, T35, T36, T37, T38, T40, T79, T93, T94, T95, T96, T106."""
import math

from formulas import (WINDOW_CAP, break_even, covered_rounds, expected_held, expected_time, hazard_window,
                      kept_rounds, nested_time, node_tail_cost, node_tail_slope, pod_break_even, pod_worst_ratio,
                      rounds, second_surge_time, separated_time, weibull_pod_cost, weibull_scale, worst_ratio)
from nested import simulate as nested, simulate_two_surges as surges

from .common import NODE, POD


def t25():
    print('T25 the headroom penalty across timing (k 30, n0 64, one pod per node; 0, 53 and 56 free slots): '
          'pod s | node s | sync s | time with none s | with 53 s | with 56 s | 53 slower than none')
    worse = n = 0
    for tp in (80, 85, 90, 95, 100):
        for tn in (200, 210, 225):
            for sync in (15, 30):
                a, b, c = (nested(30, n0=64, headroom=h, per_node=1, tau_pod=tp, tau_node=tn, sync=sync) for h in (0, 53, 56))
                n += 1
                worse += b > a
                print('  %d | %d | %d | %d | %d | %d | %s' % (tp, tn, sync, a, b, c, 'yes' if b > a else 'no'))
    print('  slower in %d of %d cases' % (worse, n))


def t26():
    print('T26 where the headroom penalty appears (n0 64, one pod per node, pod 90 s, node 210 s): k | log2(k / 2) | time with none s | with 53 s | with 56 s | penalty')
    for k in (12, 16, 20, 24, 28, 30, 31):
        a, b, c = (nested(k, n0=64, headroom=h, per_node=1) for h in (0, 53, 56))
        print('  %d | %.2f | %d | %d | %d | %s' % (k, math.log2(k / 2), a, b, c, 'yes' if b > a else 'no'))


def t27():
    print('T27 the horizontal target sets the number of node waits (k 30, n0 16, pod 90 s, node 210 s, no free '
          'slots at the start): target | g | rounds | ample s | nested s, 1 pod per node | nested s, 8 pods '
          'per node | closed s | separated s | closed s')
    for t in (0.3, 0.4, 0.5, 0.6, 0.7):
        print('  %.1f | %.2f | %d | %d | %d | %d | %d | %d | %d' % (
            t, 1 / t, rounds(30, target=t), nested(30, target=t, headroom=10 ** 6), nested(30, target=t, per_node=1),
            nested(30, target=t), nested_time(30, POD, NODE, target=t), nested(30, target=t, oracle=True),
            separated_time(30, POD, NODE, target=t)))


def t28():
    print('T28 a second 30x surge after the first is scaled down (n0 16, 8 pods per node, pod 90 s, node 210 '
          's, HPA stabilization 300 s, CA unneeded time 600 s): gap s | rounds kept | closed s | instant '
          'deletion s | bulk of 10 s | node-hours held in the gap')
    for g in (0, 150, 280, 300, 450, 600, 630, 640, 660, 675, 720, 765, 810, 855, 900, 945, 1200, 1800, 3600):
        inst, held = surges(g, bulk=10 ** 6)
        bulk, _ = surges(g)
        print('  %d | %s | %d | %d | %d | %.1f' % (g, '-' if g < 300 else kept_rounds(g, 30, POD), second_surge_time(g, 30, POD, NODE),
                                               inst, bulk, held / 3600))


def t29():
    print('T29 the unneeded time against a known gap of 1200 s (as T28, instant deletion): unneeded s | rounds kept | time s | node-hours held | dominated by')
    release = surges(1200, unneeded=0, bulk=10 ** 6)
    hold = surges(1200, unneeded=1800, bulk=10 ** 6)
    for u in (0, 60, 300, 600, 900, 1000, 1080, 1140, 1170, 1200, 1800):
        t, held = surges(1200, unneeded=u, bulk=10 ** 6)
        if (t, held) == release or (t, held) == hold:
            by = 'none'
        elif t >= release[0] and held > release[1]:
            by = 'release at once'
        elif t > hold[0] and held >= hold[1]:
            by = 'hold through the gap'
        else:
            by = 'none'
        print('  %d | %d | %d | %.2f | %s' % (u, kept_rounds(1200, 30, POD, unneeded=u), t, held / 3600, by))


SPARE, FOREVER = 58, 10 ** 9   # spare nodes the first surge of T28 leaves; an unneeded time that never expires


def t30():
    print('T30 exponential gaps between 30x surges (as T28, instant deletion; 200 gaps at the quantiles for '
          'the simulated means): mean gap s | unneeded s | expected node-hours | simulated | expected time s | '
          'simulated | exchange rate at which holding forever wins')
    for mu in (600, 1800, 7200):
        star = SPARE * mu / (rounds(30) * NODE)
        for u in (0, 300, 600, 900, 1200, 1800, 3600, FOREVER):
            runs = [surges(-mu * math.log(1 - (i + 0.5) / 200), unneeded=u, bulk=10 ** 6) for i in range(200)]
            print('  %d | %s | %.2f | %.2f | %.1f | %.1f | %.1f' % (
                mu, 'forever' if u == FOREVER else u, expected_held(u, mu, SPARE) / 3600, math.fsum(h for _, h in runs) / 200 / 3600,
                expected_time(u, mu, 30, POD, NODE), math.fsum(t for t, _ in runs) / 200, star))


def t31():
    print('T31 the worst gap (as T28, 58 spare nodes): exchange rate, node-s per s short | break-even s | '
          'worst ratio at break-even | best unneeded s, 10 s grid | its worst ratio | worst ratio at 600 s | '
          'at 0 s')
    for lam in (4, 16, 41.4, 64, 256):
        b = break_even(lam, 30, NODE, SPARE)
        best = min(range(0, 8001, 10), key=lambda u: worst_ratio(u, lam, 30, POD, NODE, SPARE))
        print('  %.1f | %.0f | %.3f | %d | %.3f | %.3f | %.3f' % (
            lam, b, worst_ratio(round(b), lam, 30, POD, NODE, SPARE), best, worst_ratio(best, lam, 30, POD, NODE, SPARE),
            worst_ratio(600, lam, 30, POD, NODE, SPARE), worst_ratio(0, lam, 30, POD, NODE, SPARE)))


def t32():
    print("T32 break-even holding when the ramp outlasts the pod loop's window (58 spare nodes, pod 90 s, node "
          '210 s, stabilization 300 s): surge | rounds | ramp (R - 1) pod s | exchange rate | break-even s | '
          'worst ratio')
    for k in (30, 100, 300):
        for lam in (4, 16, 64, 256):
            b = break_even(lam, k, NODE, SPARE)
            print('  %d | %d | %d | %d | %.0f | %.3f' % (k, rounds(k), (rounds(k) - 1) * POD, lam, b, worst_ratio(round(b), lam, k, POD, NODE, SPARE)))


def t33():
    print('T33 the same 900 s memory kept by nodes or by pods (as T28, instant deletion): gap s | nodes, '
          'stabilization 300 s and unneeded 600 s: closed s | simulated s | node-hours | pods, stabilization '
          '900 s and unneeded 0 s: closed s | simulated s | node-hours')
    for g in (150, 450, 630, 700, 850, 900, 1200):
        nt, nh = surges(g, unneeded=600, bulk=10 ** 6)
        pt, ph = surges(g, stabilization=900, unneeded=0, bulk=10 ** 6)
        print('  %d | %d | %d | %.1f | %d | %d | %.1f' % (g, second_surge_time(g, 30, POD, NODE, 300, 600), nt, nh / 3600,
                                                     second_surge_time(g, 30, POD, NODE, 900, 0), pt, ph / 3600))


def t34():
    print('T34 memoryless gaps, the memory kept as pods first up to the 3600 s cap, then as nodes: mean gap s '
          '| stabilization s | unneeded s | expected node-hours | expected time s | rate above which an hour '
          'of pods beats releasing at once | rate above which nodes kept forever beat an hour of pods')
    for mu in (600, 1800, 7200):
        lo, hi = SPARE * mu / nested_time(30, POD, NODE), SPARE * mu / (rounds(30) * NODE)
        for w, u in ((0, 0), (300, 0), (600, 0), (900, 0), (1500, 0), (3600, 0), (3600, 600), (3600, 3600), (3600, FOREVER)):
            print('  %d | %d | %s | %.2f | %.1f | %.1f | %.1f' % (
                mu, w, 'forever' if u == FOREVER else u, expected_held(u, mu, SPARE, w) / 3600, expected_time(u, mu, 30, POD, NODE, w), lo, hi))


def t35():
    print('T35 holding pods for the break-even time against the worst gap (58 spare nodes, unneeded 0 s; the '
          'window cap of 3600 s is reached at rate %.1f): exchange rate | break-even s | worst ratio' % (WINDOW_CAP * SPARE / nested_time(30, POD, NODE)))
    for lam in (4, 16, 41.4, 64, 160):
        b = pod_break_even(lam, 30, POD, NODE, SPARE)
        print('  %.1f | %.0f | %.3f' % (lam, b, pod_worst_ratio(b, lam, 30, POD, NODE, SPARE)))


SHAPES = (0.5, 0.7, 1.0, 1.5, 3.0)   # Weibull shapes of the gap: falling, constant and rising hazard


def t36():
    print('T36 the hazard rule, memory kept as pods (Weibull gaps, mean 1800 s, 58 spare nodes, cold time 1200 '
          's, window capped at 3600 s): shape | exchange rate | hazard-rule window s | best on a 10 s grid s | '
          'cost at 0, node-hours | at the best | at the cap | saving against the better end')
    for shape in SHAPES:
        for lam in (16, 64, 160):
            def cost(m):
                return weibull_pod_cost(m, shape, 1800, lam, 30, POD, NODE, SPARE)
            best = min(range(0, WINDOW_CAP + 1, 10), key=cost)
            w = hazard_window(shape, 1800, lam, 30, POD, NODE, SPARE)
            ends = min(cost(0), cost(WINDOW_CAP))
            print('  %.1f | %d | %s | %d | %.2f | %.2f | %.2f | %.1f%%' % (
                shape, lam, '-' if w is None else '%.0f' % w, best, cost(0) / 3600, cost(best) / 3600, cost(WINDOW_CAP) / 3600,
                100 * (1 - cost(best) / ends)))


def t37():
    print('T37 expected cost against the window, as a multiple of releasing at once (as T36, exchange rate 64): shape | window s | cost / cost at 0')
    for shape in SHAPES:
        c0 = weibull_pod_cost(0, shape, 1800, 64, 30, POD, NODE, SPARE)
        for m in (0, 60, 120, 240, 360, 487, 600, 900, 1200, 1800, 2400, 3000, 3600):
            print('  %.1f | %d | %.3f' % (shape, m, weibull_pod_cost(m, shape, 1800, 64, 30, POD, NODE, SPARE) / c0))


def t38():
    print('T38 the hazard rule against the simulation (shape 0.5, mean 1800 s, exchange rate 64, 300 gaps at '
          'the quantiles, instant deletion, unneeded 0 s): window s | closed cost, node-hours | simulated cost '
          '| simulated mean time s')
    eta = weibull_scale(1800, 0.5)
    gaps = [eta * (-math.log(1 - (i + 0.5) / 300)) ** 2 for i in range(300)]
    for m in (0, 120, 300, 487, 900, 1800, 3600):
        runs = [surges(g, stabilization=m, unneeded=0, bulk=10 ** 6) for g in gaps]
        print('  %d | %.2f | %.2f | %.1f' % (m, weibull_pod_cost(m, 0.5, 1800, 64, 30, POD, NODE, SPARE) / 3600,
                                         math.fsum(h + 64 * t for t, h in runs) / 300 / 3600, math.fsum(t for t, _ in runs) / 300))


def t40():
    print('T40 memory kept as nodes past the one-hour pod window (Weibull gaps, 58 spare nodes, window 3600 s; '
          'forever stands for an unneeded time of 200000 s): shape | mean gap s | exchange rate | unneeded '
          'times where the lagged rule turns upward s | best on a 50 s grid s | cost at 0, node-hours | at the '
          'best | forever | saving against the better end')
    for shape, mean in ((0.5, 3600), (0.5, 7200), (0.7, 7200)):
        for lam in (200, 500, 1000):
            slope = [node_tail_slope(u, shape, mean, lam, 30, POD, NODE, SPARE) for u in range(0, 60001, 10)]
            ups = [10 * (i + 1) for i, (a, b) in enumerate(zip(slope, slope[1:])) if a < 0 <= b]
            def cost(u):
                return node_tail_cost(u, shape, mean, lam, 30, POD, NODE, SPARE)
            best = min(range(0, 60001, 50), key=cost)
            c0, cb, cf = cost(0), cost(best), cost(200000)
            print('  %.1f | %d | %d | %s | %d | %.2f | %.2f | %.2f | %.1f%%' % (
                shape, mean, lam, ', '.join(map(str, ups)) or '-', best, c0 / 3600, cb / 3600, cf / 3600, 100 * (1 - cb / min(c0, cf))))


def t6():
    print('T6 pod loop nested in node loop, no headroom (n0 16, target 0.5, limit = request, 8 pods per node, '
          'pod 90 s, node 210 s): k | rounds | ample nodes s | nested s | closed s | separated s | closed s | '
          'cost of nesting s')
    for k in (3, 5, 10, 30, 100):
        ample, sim, sep = nested(k, headroom=10 ** 6), nested(k), nested(k, oracle=True)
        print('  %d | %d | %d | %d | %d | %d | %d | %d' % (k, rounds(k), ample, sim, nested_time(k, POD, NODE),
                                                         sep, separated_time(k, POD, NODE), sim - sep))


def t7():
    print('T7 node provisioning time, k 30: node s | nested s | closed s | separated s | ample s | nested / ample')
    ample = nested(30, headroom=10 ** 6)
    for tn in (30, 60, 120, 210, 300, 600):
        sim = nested(30, tau_node=tn)
        print('  %d | %d | %d | %d | %d | %.2f' % (tn, sim, nested_time(30, POD, tn), nested(30, tau_node=tn, oracle=True),
                                                ample, sim / ample))


def t8():
    print('T8 headroom held in advance (n0 64, one pod per node, so slots are exact): k | headroom slots | x n0 | rounds covered | time s')
    for k, slots in ((30, (0, 53, 56, 64, 169, 176, 192, 402, 416, 448, 896)), (20, (0, 53, 56, 64))):
        for h in slots:
            print('  %d | %d | %.3f | %d | %d' % (k, h, h / 64, covered_rounds(h, 64, k), nested(k, n0=64, headroom=h, per_node=1)))


def t9():
    print('T9 node size as hidden headroom, k 30, n0 16: pods per node | free slots at the start | nested s')
    for c in (2, 4, 8, 16, 32, 64):
        free = -(-16 // c) * c - 16
        print('  %d | %d | %d' % (c, free, nested(30, per_node=c)))


def t79():
    print('T79 a capacity buffer sized as a percentage of current replicas (Cluster Autoscaler CapacityBuffer '
          'API, beta since 1.35, field percentage, rounded up), specimen 16 pods, 8 to a node, 50%% target, '
          '30x surge, 90 s pod and 210 s node: percentage | slots held at rest | seconds until capacity meets '
          'the surge | seconds with the same slots held as static headroom | slots the buffer asks for at the '
          "surge's final size, 240 pods. No buffer: %d s; ample nodes: %d s" % (nested(30), nested(30, headroom=10 ** 4)))
    for pct in (10, 25, 50, 100, 200, 400, 800):
        rest = math.ceil(16 * pct / 100 - 1e-9)
        print('  %d | %d | %d | %d | %d' % (pct, rest, nested(30, buffer_pct=pct), nested(30, headroom=rest), math.ceil(240 * pct / 100 - 1e-9)))


def t93():
    print('T93 the formal side of the nested pair, surges 3x to 100x (n0 16, target 0.5, pod 90 s, node 210 s, '
          'sync 15 s, scan 10 s): k | rounds R | pod loop alone, ample slots, s | its deadline R (pod + sync) '
          '| node loop sees the final need, s | its deadline R (pod + sync + scan) + node | nested, s | R (pod '
          '+ node)')
    for k in (3, 5, 10, 30, 100):
        r = rounds(k)
        print('  %d | %d | %d | %d | %d | %d | %d | %d' % (k, r, nested(k, headroom=10 ** 5), r * 105, nested(k, oracle=True),
                                                          r * 115 + 210, nested(k), r * 300))


def t94():
    from formulas import nesting_multiplier, pareto_mean_time, pareto_rounds_tail, pareto_shortfall, ramp_shortfall
    import random
    print('T94 surge sizes Pareto with exponent alpha above the surge that saturates the running pods (k >= 2 '
          'at target 0.5, so the need is Pareto above n0 = 16); pod 90 s, node 210 s, g 2. Rows "tail": alpha '
          '| P(R >= 2) | P(R >= 4) | mean rounds | mean nested time, s | mean pod-seconds short: ample nodes | '
          'node loop sees the final need | nested | nesting multiplier on the node-wait part, 1 / (1 - 2^(1 - '
          'alpha)). Rows "ramp": k | pod-seconds short, closed form | simulated (sync and scan included). Rows '
          '"sample": alpha | surges | mean pod-seconds short over that many surges, nested, seed 1')
    for alpha in (0.69, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0):
        def f(x):
            return 'inf' if math.isinf(x) else '%.0f' % x
        m = nesting_multiplier(alpha)
        print('  tail | %.2f | %.4f | %.4f | %.3f | %.0f | %s | %s | %s | %s' % (
            alpha, pareto_rounds_tail(2, alpha), pareto_rounds_tail(4, alpha), 1.0 / (1.0 - 2.0 ** (-alpha)),
            pareto_mean_time(alpha, 90, 210), f(pareto_shortfall(alpha, 16, 90, 0)),
            f(pareto_shortfall(alpha, 16, 90, 210, separated=True)), f(pareto_shortfall(alpha, 16, 90, 210)),
            'inf' if math.isinf(m) else '%.2f' % m))
    for k in (5, 10, 30, 100):
        out = []
        nested(k, shortfall=out)
        print('  ramp | %d | %.0f | %.0f' % (k, ramp_shortfall(k, 16, 90, 210), out[0]))
    for alpha in (0.69, 1.5):
        rng = random.Random(1)
        acc, marks = [], {100, 1000, 10000, 100000}
        for i in range(1, 100001):
            acc.append(ramp_shortfall(2.0 * (1.0 - rng.random()) ** (-1.0 / alpha), 16, 90, 210))
            if i in marks:
                print('  sample | %.2f | %d | %.0f' % (alpha, i, math.fsum(acc) / i))


def t95():
    from formulas import cover_cost, optimal_cover
    print('T95 the headroom frontier over the tail: slots covering c rounds, 16 (2^c - 1), held for a mean gap '
          'of 3600 s between surges, against price slot-seconds per pod-second short in the mean ramp (pod 90 '
          's, node 210 s). Rows: price | alpha | x* = 1 + slots / n0 at the continuous optimum | best whole '
          'rounds c | slots | expected cost per surge, slot-seconds | node-wait part kept by each further '
          'round, 2^(1 - alpha)')
    for price in (10, 100, 1000):
        for alpha in (1.1, 1.2, 1.5, 2.0, 3.0):
            x, c = optimal_cover(alpha, price, 3600, 210)
            print('  %d | %.1f | %.2f | %d | %d | %.0f | %.3f' % (price, alpha, x, c, 16 * (2 ** c - 1),
                                                               cover_cost(c, alpha, 16, price, 3600, 90, 210), 2 ** (1 - alpha)))


def t96():
    import statistics
    from formulas import censored_naive, censoring_crossing
    from tail_buffer import run
    print('T96 a buffer controller that estimates the tail exponent after every surge by maximum likelihood '
          'and holds the optimal cover for it (price 100, mean gap 3600 s, buffer limit 8 rounds, 1000 surges, '
          'seeds 1 to 20). Rows "policy": alpha | rule | median over seeds of the expected cost per surge over '
          'the oracle\'s | final cover, seed 1. Rows "sample": alpha | median over seeds of the realised mean '
          'cost over the expected, oracle cover. Rows "censor": alpha | cap on the reading, k | naive '
          'estimate, closed form | naive, seed 1 | censored estimate, seed 1. Rows "cross": cap, k | lowest '
          'exponent whose naive reading is 1 or more. Rows "pin": alpha | cover held after 1000 surges, buffer '
          'limit 8 rounds, seed 1')
    for alpha in (1.2, 1.5, 2.0, 3.0):
        oracle = [run(alpha, rule='oracle', surges=1000, seed=s) for s in range(1, 21)]
        for rule in ('oracle', 'mle', 'fixed', 'peak'):
            outs = oracle if rule == 'oracle' else [run(alpha, rule=rule, surges=1000, seed=s) for s in range(1, 21)]
            ratio = statistics.median(o['expected_cost'] / b['expected_cost'] for o, b in zip(outs, oracle))
            print('  policy | %.1f | %s | %.3f | %d' % (alpha, rule, ratio, outs[0]['final_c']))
        print('  sample | %.1f | %.3f' % (alpha, statistics.median(o['mean_cost'] / o['expected_cost'] for o in oracle)))
    for alpha, cap in ((0.69, 10.0), (0.69, 20.0), (0.8, 10.0), (0.9, 20.0), (1.5, 20.0)):
        naive = run(alpha, rule='mle', surges=1000, cap=cap, fix=False)['alpha_hat']
        fixed = run(alpha, rule='mle', surges=1000, cap=cap)['alpha_hat']
        print('  censor | %.2f | %.0f | %.3f | %.3f | %.3f' % (alpha, cap, censored_naive(alpha, 2.0, cap), naive, fixed))
    for cap in (10.0, 20.0, 50.0):
        print('  cross | %.0f | %.3f' % (cap, censoring_crossing(2.0, cap)))
    for alpha in (0.69, 0.9):
        print('  pin | %.2f | %d' % (alpha, run(alpha, rule='mle', surges=1000)['final_c']))


def t106():
    from formulas import pareto_shortfall_slots
    print('T106 the headroom frontier in slots rather than whole rounds: surges Pareto above the saturating '
          'surge, n0 16, pod 90 s, node 210 s, a round covered when the pods it adds fit in the free slots. '
          'Rows "step": alpha | slots at a whole round\'s price | mean pod-seconds short one slot below | at it '
          '| drop. Rows "tread": alpha | slots | mean pod-seconds short. Rows "best": alpha | slots minimizing '
          '3600 x slots + 100 x mean shortfall over 0 to 2999 | its cost per surge')
    for alpha in (1.5, 2.0):
        for h in (16, 48, 112, 240, 496):
            a, b = pareto_shortfall_slots(alpha, 16, 90, 210, h - 1), pareto_shortfall_slots(alpha, 16, 90, 210, h)
            print('  step | %.1f | %d | %.0f | %.0f | %.3f' % (alpha, h, a, b, 1 - b / a))
        for h in (16, 20, 30, 40, 47):
            print('  tread | %.1f | %d | %.0f' % (alpha, h, pareto_shortfall_slots(alpha, 16, 90, 210, h)))
        def cost(h):
            return 3600.0 * h + 100.0 * pareto_shortfall_slots(alpha, 16, 90, 210, h)
        best = min(range(3000), key=cost)
        print('  best | %.1f | %d | %.0f' % (alpha, best, cost(best)))


def t121():
    from formulas_time import headroom_for, rounds, step_slots
    from nested import simulate as nested_sim
    print('T121 the two headroom thresholds (n0 64, target 0.5, one pod per node, pod 90 s, node 210 s): k | rounds covered c | '
          'slots that keep the first c rounds free of pending pods, n0 (g^c - 1) | fewest slots that remove c node waits, '
          'ceil(need g^(c - R)) - n0 | seconds to capacity with that many slots | with one slot fewer')
    for k in (10, 16, 30):
        for c in range(1, rounds(k) + 1):
            h = step_slots(c, 64, k)
            print('  %d | %d | %d | %d | %d | %d' % (k, c, headroom_for(c, 64, k), h,
                                                      nested_sim(k, n0=64, headroom=h, per_node=1),
                                                      nested_sim(k, n0=64, headroom=h - 1, per_node=1)))
