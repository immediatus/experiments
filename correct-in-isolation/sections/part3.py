"""Sections of Part 3, a shared state: T10, T11, T12, T41, T42, T43, T44, T45, T46, T57, T65, T66, T67, T68, T69, T70, T86, T87, T97, T98, T99, T104, T105, T108."""
import math

from formulas import (backlog, failed_list_rate, failed_state_delay, failed_state_possible,
                      fresh_rejections_to_pass, no_bookmark_gone_probability, no_bookmark_load,
                      pages_before_expiry, rejections_before_gone, saturated_storm_possible, second_wave,
                      watch_cache_span)
from relist import (simulate as relist, simulate_fair as relist_fair, simulate_limited as relist_limited,
                    simulated_no_bookmark_gone)

from .common import CLIENTS, MEAN, RETENTION, SEATS, SHORT


def t10():
    print('T10 informers re-listing behind a queued API server (2000 clients, capacity 100 seat-s/s, history '
          '300 s, watch 300 to 600 s, every client forced to LIST at t 0): LIST cost seat-s | backlog s | '
          'second wave | failed state possible | LISTs hour 1 | LISTs hour 8 | largest delay s')
    for cost in (10, 30, 31, 40, 50, 60, 80, 90, 100, 150, 200):
        per_hour, worst = relist(float(cost))
        print('  %d | %.0f | %s | %s | %d | %d | %.0f' % (
            cost, backlog(cost, CLIENTS, SEATS), 'yes' if second_wave(cost, CLIENTS, SEATS, RETENTION, SHORT) else 'no',
            'yes' if failed_state_possible(cost, CLIENTS, SEATS, RETENTION, MEAN) else 'no', per_hour[0], per_hour[-1], worst))


def t11():
    print('T11 does the trigger reach the failed state (LISTs still running in hour 8): LIST cost | '
          'failed-state delay s | pulse | spread 450 s | spread 900 s | spread 1800 s')
    for cost in (50, 55, 60, 70, 80, 90, 100):
        row = ['sustained' if relist(float(cost), spread=sp)[0][-1] else 'recovers' for sp in (0.0, 450.0, 900.0, 1800.0)]
        print('  %d | %.0f | %s' % (cost, failed_state_delay(cost, CLIENTS, SEATS, MEAN), ' | '.join(row)))


def t12():
    print('T12 each safeguard alone, LIST cost 100: case | LISTs in 8 hours | LISTs per hour at the end | failed-state rate per hour')
    for name, kw in (('overload protection with ample capacity', {'capacity': SEATS * 100}),
                     ('re-list on 410 with history that never expires', {'retention': 10.0 ** 9}),
                     ('both, as documented', {})):
        per_hour, _ = relist(100.0, **kw)
        print('  %s | %d | %d | %.0f' % (name, sum(per_hour), per_hour[-1], failed_list_rate(100.0, SEATS) * 3600))


def t41():
    print('T41 the queue with its wait limit (as T10; 15 s wait limit then 429, Reflector backoff; fair '
          'queuing at the system level: 64 queues, hand 6, queue length 50): LIST cost | backlog s | saturated '
          'storm possible | idealized queue: LISTs hour 1 | hour 8 | wait limit, one queue: hour 1 | hour 8 | '
          '410s | fair queuing: hour 1 | hour 8 | 410s')
    for cost in (30, 31, 35, 40, 50, 70, 90, 100, 110, 112, 114, 116, 120, 150, 200):
        ideal, limited, fair = relist(float(cost)), relist_limited(float(cost)), relist_fair(float(cost))
        print('  %d | %.0f | %s | %d | %d | %d | %d | %d | %d | %d | %d' % (
            cost, backlog(cost, CLIENTS, SEATS), 'yes' if saturated_storm_possible(cost, CLIENTS, SEATS, RETENTION, MEAN) else 'no',
            ideal[0][0], ideal[0][-1], limited[0][0], limited[0][-1], limited[1], fair[0][0], fair[0][-1], fair[1]))


def t42():
    print('T42 where the second wave starts with the wait limit (pulse, 3 hours): LIST cost | backlog s | '
          'idealized second wave | 410s, one queue, seeds 1 2 3 | 410s, fair queuing, seeds 1 2 3')
    for cost in range(30, 41):
        print('  %d | %.0f | %s | %s | %s' % (cost, backlog(cost, CLIENTS, SEATS), 'yes' if second_wave(cost, CLIENTS, SEATS, RETENTION, SHORT) else 'no',
                                         ' '.join(str(relist_limited(float(cost), hours=3, seed=s)[1]) for s in (1, 2, 3)),
                                         ' '.join(str(relist_fair(float(cost), hours=3, seed=s)[1]) for s in (1, 2, 3))))


def t43():
    print('T43 does the trigger decide the storm (LISTs in hour 8; trigger spread 0, 450, 900, 1800 s): LIST cost | idealized queue | wait limit, one queue')
    for cost in (90, 100, 110, 112, 114, 116, 120, 150):
        def row(sim):
            return ' '.join(str(sim(float(cost), spread=sp)[0][-1]) for sp in (0.0, 450.0, 900.0, 1800.0))
        print('  %d | %s | %s' % (cost, row(relist), row(relist_limited)))


def t44():
    print('T44 partial triggers (a fraction of clients forced to LIST at t 0; LISTs in hour 8): LIST cost | fraction | idealized queue | wait limit, one queue')
    for cost in (120, 150):
        for frac in (0.25, 0.3, 0.4, 0.5, 1.0):
            print('  %d | %.2f | %d | %d' % (cost, frac, relist(float(cost), forced=frac)[0][-1], relist_limited(float(cost), forced=frac)[0][-1]))


def t45():
    print('T45 consecutive rejections behind a re-watch answered 410 (history 300 s): closed-form least, any '
          'backoff state %d; fresh backoff, a 410 needs at least %d and %d always produce one | LIST cost | '
          'one queue: fewest, most | fair queuing: fewest, most' % (
        (rejections_before_gone(RETENTION),) + fresh_rejections_to_pass(RETENTION)))
    for cost in (40, 100, 150):
        a, b = relist_limited(float(cost), hours=3)[4], relist_fair(float(cost), hours=3)[4]
        print('  %d | %d, %d | %d, %d' % (cost, a[0], a[1], b[0], b[1]))


def t46():
    print('T46 why the onset is sharp (wait limit, one queue, pulse trigger; attempts after the first hour): '
          'LIST cost | share of re-watch attempts rejected | share of LIST attempts rejected | p^11 | p^15, p '
          'the re-watch share, the fewest and the most rejections a fresh client can lose before a 410 | '
          're-watches answered 410 per hour')
    for cost in (100, 110, 112, 114, 116, 120, 150, 200):
        r = relist_limited(float(cost))
        (wa, wr), (la, lr) = r[5]['watch'], r[5]['list']
        p = wr / wa
        print('  %d | %.3f | %.3f | %.2f | %.2f | %.0f' % (cost, p, lr / la, p ** 11, p ** 15, r[1] / 8))


def t57():
    print('T57 how much history a watch through the watch cache has, and what the shared state does with less '
          '(as T41: 2000 informers, capacity 100 seat-s/s, watches 300 to 600 s, wait limit 15 s, Reflector '
          'backoff, one queue). Rows "rate": events per second | seconds of history the cache holds at that '
          'steady rate. Rows "history": seconds | idealized second-wave list cost | storm list cost under any '
          'order of service | rejections a 410 needs, any backoff state | least list cost at which a sudden '
          'trigger sustains a storm (LISTs in hour 8 above 0; one below has none) | of the trigger spreads 0, '
          '450, 900, 1800 s, how many sustain it there | LISTs in hour 8 at the specimen list cost 100')
    for rate in (0.1, 0.5, 1.0, 3.0, 10.0, 50.0, 300.0, 1000.0, 5000.0):
        print('  rate %g | %.1f' % (rate, watch_cache_span(rate)))
    for retention in (300.0, 150.0, 75.0):
        def storms(c, sp=0.0):
            return relist_limited(float(c), retention=retention, spread=sp)[0][-1] > 0
        lo, hi = 30, 120
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if storms(mid):
                hi = mid
            else:
                lo = mid
        assert storms(hi) and not storms(hi - 1)
        spreads = sum(storms(hi, sp) for sp in (0.0, 450.0, 900.0, 1800.0))
        print('  history %.0f | %.2f | %.2f | %d | %d | %d | %d' % (retention, (SHORT + retention) * 100.0 / CLIENTS, (MEAN + retention) * 100.0 / CLIENTS,
                                                      rejections_before_gone(retention), hi, spreads, relist_limited(100.0, retention=retention)[0][-1]))


def t65():
    print('T65 a paginated list in a saturated queue (each page waits the full 15 s wait limit, the best case; '
          "the pager's default page size 500): seconds of history | pages served before the first page's "
          'resourceVersion leaves the history | objects they hold')
    for h in (300.0, 150.0, 75.0):
        pages, objects = pages_before_expiry(h)
        print('  %.0f | %d | %d' % (h, pages, objects))


def t66():
    print('T66 how long a storm lasts near its onset (as T41: wait limit, one queue, sudden trigger forcing '
          'every informer to list; 72 simulated hours, seeds 1 to 10): LIST cost | storms still running in '
          'hour 8 | storms that end within 72 hours | hours at which they end (first hour with no list) | '
          'storms still running in hour 72')
    for cost in (113, 114, 115):
        ends, at8, running = [], 0, 0
        for seed in range(1, 11):
            h = relist_limited(float(cost), hours=72, seed=seed)[0]
            at8 += h[7] > 0
            end = next((i for i in range(1, len(h)) if h[i] == 0), None)
            if end is None:
                running += 1
            else:
                ends.append(end + 1)
        print('  %d | %d | %d | %s | %d' % (cost, at8, len(ends), ' '.join(map(str, sorted(ends))) or '-', running))


def t67():
    print("T67 the storm onset when the informers' priority level gets a share of the server (as T41: 2000 "
          'informers, wait limit, one queue, sudden trigger; capacity 100 seat-s/s in all): share of capacity '
          '| seat-s/s | least list cost at which a storm is still running in hour 8 (one below has none) | '
          'backlog at that cost, s')
    for share in (1.0, 0.5, 0.25):
        cap = 100.0 * share
        def storms(c):
            return relist_limited(float(c), capacity=cap)[0][-1] > 0
        lo, hi = 5, 130
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if storms(mid):
                hi = mid
            else:
                lo = mid
        assert storms(hi) and not storms(hi - 1)
        print('  %.2f | %.0f | %d | %.0f' % (share, cap, hi, backlog(hi, CLIENTS, cap)))


def t68():
    print('T68 informers of mixed sizes with the same total forced work as the specimen (1900 small and 100 '
          'large, each large list a fixed multiple of a small one; wait limit, sudden trigger, capacity 100 '
          'seat-s/s): size ratio | queue | onset as the uniform list cost of the same total work (storm still '
          'running in hour 8; one below has none) | seconds one large list holds the server at the onset | '
          're-watches answered 410 per small informer | per large informer')
    def mix(c, ratio, small=1900, large=100):
        cs = 2000 * c / (small + large * ratio)
        return [cs] * small + [cs * ratio] * large
    for ratio in (20.0, 100.0):
        for name, sim in (('one queue', relist_limited), ('fair queuing', relist_fair)):
            def storms(c):
                return sim(mix(float(c), ratio))[0][-1] > 0
            lo, hi = 90, 130
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if storms(mid):
                    hi = mid
                else:
                    lo = mid
            assert storms(hi) and not storms(hi - 1)
            g = sim(mix(float(hi), ratio))[-1]['gone']
            print('  %.0f | %s | %d | %.1f | %.2f | %.2f' % (ratio, name, hi, mix(float(hi), ratio)[-1] / 100.0,
                                                       math.fsum(g[:1900]) / 1900, math.fsum(g[1900:]) / 100))


def t69():
    print('T69 how long the second wave lasts below the storm (as T41: wait limit, one queue, sudden trigger; '
          '8 hours): LIST cost | re-watches answered 410 | minutes until the last 410 | LISTs in hours 1, 2, 3 '
          '| minutes until the last 410 times the square root of (113 - LIST cost), 113 the onset of T57')
    for cost in (40, 50, 70, 90, 100, 110, 112):
        r = relist_limited(float(cost))
        minutes = r[-1]['last_gone'] / 60.0
        print('  %d | %d | %.1f | %s | %.0f' % (cost, r[1], minutes, ' '.join(str(x) for x in r[0][:3]), minutes * math.sqrt(113 - cost)))


def t70():
    print('T70 re-watches with no bookmarks and no trigger (a selector seeing Poisson events; watches of 300 '
          "to 600 s; the specimen's 2000 informers, LIST 100 seat-s, capacity 100 seat-s/s, mean watch 450 s): "
          'history s | matching events per hour | share of re-watches answered 410, exp(-lam T_h) | simulated, '
          '20000 watches | steady list load as a share of capacity. Last rows: history s | events per hour '
          'below which the steady load exceeds capacity')
    for h in (300.0, 150.0):
        for per_hour in (0.0, 1.0, 6.0, 12.0, 18.0, 30.0, 60.0):
            lam = per_hour / 3600.0
            sim = simulated_no_bookmark_gone(lam, h) if h == 300.0 else float('nan')
            print('  %.0f | %g | %.3f | %s | %.3f' % (h, per_hour, no_bookmark_gone_probability(lam, h),
                                                   '%.3f' % sim if h == 300.0 else '-', no_bookmark_load(lam, h)))
    for h in (300.0, 150.0):
        print('  critical %.0f | %.1f' % (h, 3600.0 * math.log(2000 * 100.0 / 100.0 / 450.0) / h))


def t86():
    from formulas import level_limits, list_seats, list_time_threshold
    print('T86 prices in seats on a server of 600 seats, the default --max-requests-inflight 400 plus '
          '--max-mutating-requests-inflight 200, the default priority levels, and SizeBasedListCostEstimate: '
          'level | nominal concurrency limit, seats | most seats one request may take')
    levels = level_limits()
    for name, (cl, mx) in levels.items():
        print('  %s | %d | %d' % (name, cl, mx))
    print('  seats charged a list served from the watch cache, any collection of 1 MB or more: %d; the same list from storage, 150,000 objects of 20 kB, at workload-low: %d' % (list_seats(150000, 20000, True, levels['workload-low'][1]), list_seats(150000, 20000, False, levels['workload-low'][1])))
    print('  execution time per list, s, at which a full trigger reaches a backlog of 750 s (Proposition 21 with the specimen\'s watches and five minutes of history) | and 2,260 s (the onset the specimen\'s simulation found with the whole server): clients | level | informers')
    for who, level in (('kubelets', 'system'), ('a DaemonSet that watches all pods', 'workload-low')):
        cl, mx = levels[level]
        seats = list_seats(10 ** 6, 1, True, mx)
        for n in (1000, 5000, 15000):
            print('  %s | %s | %d | %.2f | %.2f' % (who, level, n, list_time_threshold(n, seats, cl, 750.0), list_time_threshold(n, seats, cl, 2260.0)))


def t87():
    from relist import simulate_limited as limited
    costs = list(range(100, 160, 2)) + list(range(160, 401, 5))

    def onset(**kw):
        first_any = None
        for c in costs:
            got = [limited(float(c), seed=seed, **kw)[0][-1] >= 0.9 * 100.0 / c * 3600 for seed in (1, 2, 3, 4)]
            if any(got) and first_any is None:
                first_any = c
            if all(got):
                return first_any, c
        return first_any, None
    print('T87 partial and rolling triggers, the specimen with the wait limit, a storm counted when hour 8 '
          'runs at least 90% of capacity on LISTs, four seeds, list costs 100 to 158 in steps of 2 and 160 to '
          '400 in steps of 5. Rows "share": one sudden wave forcing that share of the informers | list cost at '
          "which some seed storms | at which every seed storms | the forced share's own backlog at those "
          'costs, share x 20 x cost, s. Rows "rolling": three waves of a third each, the second and third that '
          'many seconds after the first (a rolling restart of three API servers whose informers resume against '
          'the restarted server) | the two onsets')
    for share in (1 / 9, 1 / 6, 1 / 4, 1 / 3, 1 / 2, 1.0):
        a, b = onset(forced=share)
        print('  share | %.3f | %s | %s | %s | %s' % (share, a, b, '%.0f' % (share * 20 * a) if a else '-', '%.0f' % (share * 20 * b) if b else '-'))
    for gap in (60, 300, 600, 1800):
        a, b = onset(waves=tuple((k * float(gap), 1 / 3) for k in range(3)))
        print('  rolling | %d | %s | %s' % (gap, a, b))


def t97():
    print('T97 both safeguards keep their contracts in a storm (sudden full trigger, the server with its wait '
          "limit and the client's backoff, 8 hours): list cost | LISTs in hour 8 | re-watches answered 410 in "
          'hour 8 | longest an admitted request waited to start, s | fewest LISTs any informer completed | '
          'informers answered 410 more than an hour before the end and not listed since')
    for cost in (114.0, 130.0, 150.0, 200.0):
        out = relist_limited(cost)
        e = out[6]
        print('  %.0f | %d | %d | %.3f | %d | %d' % (cost, out[0][-1], e['gone_per_hour'][-1], e['worst_admitted_wait'], min(e['lists']), e['stranded']))


def t98():
    import random
    from tail_lists import pareto_costs, storm_share
    print('T98 list costs Pareto with exponent alpha, one cost per informer, mean set so that 2,000 informers '
          'average a backlog of 2,260 s (the onset of identical informers). Rows "boundary": alpha | clusters '
          'run (seeds 1 to 40) | lowest backlog that stormed, s | highest that stayed calm, s | clusters on '
          'the wrong side of 2,240 to 2,290 s: backlog and largest list cost, seat-seconds. A storm is a 410 '
          'in hour 8. Rows "share": alpha | informers | share of 2,000 clusters, mean cost 112.5, whose '
          'backlog passes 2,250 s')
    for alpha in (3.0, 2.0, 1.5, 1.2):
        pts = []
        for seed in range(1, 41):
            c = pareto_costs(2000, alpha, 113.0, random.Random(700 + seed))
            pts.append((math.fsum(c) / 100.0, relist_limited(c, seed=seed)[6]['gone_per_hour'][-1] > 0, max(c)))
        storm = [b for b, x, _ in pts if x]
        calm = [b for b, x, _ in pts if not x]
        odd = ['%.0f %.0f' % (b, m) for b, x, m in pts if (x and b < 2240) or (not x and b > 2290)]
        print('  boundary | %.1f | %d | %.0f | %.0f | %s' % (alpha, len(pts), min(storm), max(calm), '; '.join(odd) or 'none'))
    for alpha in (3.0, 2.0, 1.5, 1.2):
        for n in (1000, 1500, 1800, 2000, 2200, 2500, 3000):
            print('  share | %.1f | %d | %.3f' % (alpha, n, storm_share(n, alpha, trials=2000)))


def t99():
    print('T99 a controller that moves LISTs to a priority level of their own while 410s persist (every 10 s '
          'it counts the 410s of the last 60 s; above 0.1 per second it splits, LISTs taking the share of '
          'capacity and watches the rest; it merges after the hold with no 410). Sudden full trigger, 8 hours: '
          'list cost | controller | re-watches answered 410 | minutes until the last 410 | switches | LISTs in '
          'hours 1 to 3 | LISTs in hour 8')
    base = {'on_rate': 0.1, 'window': 60.0, 'period': 10.0, 'hold': 1800.0, 'share': 0.5}
    for cost in (40.0, 100.0, 114.0, 130.0, 150.0, 200.0):
        for name, ctrl in (('none', None), ('share 0.5, hold 1800 s', base), ('share 0.5, no hold', dict(base, hold=0.0)),
                           ('share 0.25, hold 1800 s', dict(base, share=0.25))):
            out = relist_limited(cost, controller=ctrl)
            e = out[6]
            print('  %.0f | %s | %d | %.1f | %d | %s | %d' % (cost, name, out[1], e['last_gone'] / 60.0, e['switches'],
                                                       ', '.join(str(x) for x in out[0][:3]), out[0][-1]))


def t104():
    import random
    from percolation import gen_needs, greedy_relaxation, pareto_weights, relax, stranded
    print('T104 frontiers of the controllers of Parts 3 and 4. Rows "hold": the split controller of T99 (share '
          '0.5) with the hold varied: list cost | hold, s | re-watches answered 410 | minutes split | switches '
          '| storm in hour 8. Rows "band": list cost 200 | hold, s | seeds 1 to 3 still storming in hour 8. '
          'Rows "relax": the greedy relaxation of T101 at two needs per component, its first k components '
          'relaxed: weights | k | components still stranded')
    base = {'on_rate': 0.1, 'window': 60.0, 'period': 10.0, 'share': 0.5}
    for cost in (150.0, 200.0):
        for hold in (0, 60, 120, 300, 600, 1200, 1800, 3600):
            out = relist_limited(cost, controller=dict(base, hold=float(hold)))
            e = out[6]
            print('  hold | %.0f | %d | %d | %.1f | %d | %s' % (cost, hold, out[1], e['split_seconds'] / 60.0, e['switches'],
                                                          'yes' if e['gone_per_hour'][-1] > 0 else 'no'))
    for hold in (60, 90, 120, 150, 240, 300, 360, 420, 450, 600):
        runs = [relist_limited(200.0, seed=sd, controller=dict(base, hold=float(hold)))[6]['gone_per_hour'][-1] for sd in (1, 2, 3)]
        print('  band | 200 | %d | %d' % (hold, sum(1 for x in runs if x > 0)))
    for label, exponent in (('equal', None), ('Pareto 1.8', 1.8)):
        rng = random.Random(0)
        w = [1.0] * 1000 if exponent is None else pareto_weights(1000, exponent, rng)
        needs = gen_needs(2.0, w, rng)
        order = greedy_relaxation(needs)
        for k in sorted({x for x in (0, 1, 2, 4, 8, 16, 24, 32, 48) if x <= len(order)} | {len(order) - 2, len(order) - 1, len(order)}):
            print('  relax | %s | %d | %d' % (label, k, len(stranded(relax(needs, order[:k])))))


def t105():
    print('T105 a storm spreading from the informers a trigger forced to those it never touched: one sudden '
          'wave forcing a third of the informers (the share behind one zone, or one server of three), the '
          'server with its wait limit. Rows: list cost | hours run | informers forced | re-watches answered '
          '410, forced informers | the same, informers never forced | informers never forced answered 410 at '
          'least once')
    for cost in (100.0, 142.0, 150.0):
        for hours in (1, 2, 4, 8):
            e = relist_limited(cost, waves=[(0.0, 1.0 / 3.0)], hours=hours)[6]
            forced = sum(g for g, f in zip(e['gone'], e['forced']) if f)
            never = sum(g for g, f in zip(e['gone'], e['forced']) if not f)
            touched = sum(1 for g, f in zip(e['gone'], e['forced']) if g and not f)
            print('  %.0f | %d | %d | %d | %d | %d' % (cost, hours, sum(e['forced']), forced, never, touched))


def _hyst_run(args):
    cost, warm, seed = args
    out = relist_limited(116.0 if warm else cost, seed=seed, cost_switch=(3600.0, cost) if warm else None)
    return cost, warm, seed, out[0][-1]


def t108():
    from formulas import meanfield_onset
    print('T108 Part 3\'s storm onset as a mean-field fold, and its memory. Rows "fold": backoff state a run '
          'starts in | rejections a re-watch must lose, mean jitter | backlog at the fold, s | list cost at '
          'the fold | rejection probability at the fold. Rows "admitted": the fresh fold with the served '
          'attempt\'s own queue wait added to the re-watch and to the list: wait, s | backlog at the fold, s | '
          'list cost at the fold. Rows "sweep": list cost | sudden trigger at that '
          'cost, seeds 1 to 4 still listing in hour 8 | storm entered at 116 and lowered to that cost after an '
          'hour, the same')
    for raised in (False, True):
        b, cost, p, n = meanfield_onset(raised=raised)
        print('  fold | %s | %d | %.0f | %.1f | %.3f' % ('raised' if raised else 'fresh', n, b, cost, p))
    for wait in (7.5, 15.0):
        b, cost, _, _ = meanfield_onset(admitted_wait=wait)
        print('  admitted | %.1f | %.0f | %.1f' % (wait, b, cost))
    from concurrent.futures import ProcessPoolExecutor
    costs = (100.0, 106.0, 110.0, 111.0, 112.0, 113.0)
    jobs = [(c, w, sd) for c in costs for w in (False, True) for sd in (1, 2, 3, 4)]
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(_hyst_run, jobs))
    for c in costs:
        cold = sum(1 for cc, w, sd, v in res if cc == c and not w and v > 0)
        warm = sum(1 for cc, w, sd, v in res if cc == c and w and v > 0)
        print('  sweep | %.0f | %d | %d' % (c, cold, warm))
