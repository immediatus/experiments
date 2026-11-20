"""Sections of Part 6, the whole: T17, T18, T53, T54, T55, T56, T73, T74, T75, T81, T88, T109, T110, T111, T112, T115, T116, T117."""
import itertools
import math
import random
from concurrent.futures import ProcessPoolExecutor

import hpa_vpa
import relist
from admission import admit, digest, fact_webhooks, outcomes, pod, sidecar, signer, typed_chain
from audit import SURVEY_DEFAULTS, config_order, cyclic_components, default_start_graph, enabling_depth, pairwise_relative_gains, relative_gains
from formulas import (
    backlog,
    bind_probability,
    covered_rounds,
    custom_metric_relative_gain,
    doubling_bracket,
    equilibrium_band,
    fact_passes,
    failed_state_possible,
    headroom_for,
    informers_to_bind,
    matched_tolerance,
    nested_time,
    pair_gain_at_singular,
    resting_rounds,
    rounds,
    second_wave,
    separated_time,
    singular_coupling,
    spread_order,
    step_factor,
    step_interval,
    stopping_scale_up_tolerance,
    subset_facts,
    subset_gain,
    symmetric_gain,
    vpa_utilisation,
)
from formulas_signal import split_gain_matrix
from incomplete import omit_needs, omit_prereqs, random_facts, signal_flips
from interaction import assumption_order, determinant, order_order, signal_order, signal_set_passes, state_order
from nested import simulate as nested
from percolation import gen_needs, pareto_weights, stranded
from ratios import assumption_ratio, order_ratio, signal_ratio, state_ratio, time_ratio
from recovery import recover
from relist import simulate_limited as relist_limited
from supervisor_whole import greedy, joint
from tail_lists import pareto_costs

from .common import CLIENTS, MEAN, NODE, POD, RETENTION, SEATS, SHORT


def t17():
    print('T17 every pair passes, the whole fails: seam | three mechanisms | pairwise verdicts | whole-system verdict')
    for a in (-0.3, -0.45, -0.49, -0.5, -0.6):
        g = [[1, a, a], [a, 1, a], [a, a, 1]]
        pairs = pairwise_relative_gains(g)
        whole = relative_gains(g)
        print('  signal | three loops, coupling %.2f | every pair %.3f | %s' % (
            a, pairs[(0, 1)], 'singular' if whole is None else '%.3f' % whole[0][0]))
    needs = {'webhook A': {'webhook C'}, 'webhook B': {'webhook A'}, 'webhook C': {'webhook B'}}
    place = {'webhook A': {0}, 'webhook B': {1}, 'webhook C': {2}}
    pair_stranded = [len(recover({x: place[x] for x in p}, {x: needs[x] & set(p) for x in p}, {0, 1, 2}))
                     for p in itertools.combinations(sorted(needs), 2)]
    print('  assumption | A needs C, B needs A, C needs B to start | stranded after full failure: %s | %d stranded; one start-time cycle among %s' % (
        ', '.join(map(str, pair_stranded)), len(recover(place, needs, {0, 1, 2})),
        ', '.join(sorted(cyclic_components(needs)[0]))))
    ws = [sidecar, digest, signer]
    pair_objects = [len(outcomes(list(p), passes=2)) for p in itertools.combinations(ws, 2)]
    print('  order | sidecar, digest pin, signer under the contract | admitted objects: %s | %d admitted objects; enabling depth %d' % (
        ', '.join(map(str, pair_objects)), len(outcomes(ws, passes=2)),
        enabling_depth({'sidecar': {'digest', 'signer'}, 'digest': {'signer'}})))


def t18():
    print('T18 seam audit of one cluster, every verdict from the laws of Parts 1 to 5: seam | inputs | test | verdict')
    lo, hi = equilibrium_band(q=1.0)
    fast, slow = doubling_bracket(0.5)
    print('  signal | HPA target 0.5 and VPA on CPU, margin 0.15, q 1.0, tolerance 0.1, half-life 24 h (the cluster of T3) | target inside [%.3f, %.3f] | %s: replicas step up every %.1f h, doubling every %.1f to %.1f h' % (
        lo, hi, 'outside' if not lo <= 0.5 <= hi else 'inside', step_interval(), fast, slow))
    print('  time scale | 16 pods, 30x surge, pod 90 s, node 210 s, no headroom | nested against separated | %d s against %d s; covering every round takes %d slots (%.0f x the pods)' % (
        nested_time(30, POD, NODE), separated_time(30, POD, NODE), headroom_for(rounds(30), 16, 30),
        headroom_for(rounds(30), 16, 30) / 16))
    b = backlog(100.0, CLIENTS, SEATS)
    at, onset = relist_limited(100.0), relist_limited(114.0)
    print('  state | 2000 informers, capacity 100 seat-s/s, LIST 100 seat-s, history 300 s, watch 300 to 600 s, wait limit 15 s | backlog %.0f s against %.0f s and %.0f s; the queue with its wait limit | idealized: second wave %s, failed state %s; with the wait limit: %d LISTs in hour 8 and %d re-watches answered 410; at LIST 114, %d LISTs in hour 8' % (
        b, SHORT + RETENTION, MEAN + 2 * RETENTION, 'yes' if second_wave(100.0, CLIENTS, SEATS, RETENTION, SHORT) else 'no',
        'possible' if failed_state_possible(100.0, CLIENTS, SEATS, RETENTION, MEAN) else 'impossible',
        at[0][-1], at[1], onset[0][-1]))
    cyc = cyclic_components({'A': {'C'}, 'B': {'A'}, 'C': {'B'}})
    print('  assumption | three webhooks, each checking the next one\'s pods, one replica each on distinct nodes of 100 | start-time cycles: %d of size %d | stranded with probability %.4f after 30 random node failures, %.0f after a full restart' % (
        len(cyc), len(cyc[0]), bind_probability(100, 3, 30), bind_probability(100, 3, 100)))
    configs = {'admission-signer': ['signer'], 'image-digest': ['digest'], 'sidecar-injector': ['sidecar']}
    order = config_order(configs)
    facts = {'proxy container': ('sidecar', set()), 'proxy pinned': ('digest', {'proxy container'}),
             'signature over the pinned proxy': ('signer', {'proxy pinned'})}
    hooks = {'sidecar': sidecar, 'digest': digest, 'signer': signer}
    admitted = admit(pod(), [hooks[w] for w in order], passes=2)
    fixed = all(w(admitted) == admitted for w in hooks.values())
    converging = sum(fact_passes(o, facts) <= 2 for o in itertools.permutations(order))
    print('  order | configurations admission-signer, image-digest, sidecar-injector, all IfNeeded, two passes | order by name %s; passes needed %d against 2 | admitted object %s; %d of 6 orders converge' % (
        ', '.join(order), fact_passes(order, facts), 'a common fixed point' if fixed else 'not a common fixed point', converging))


def t53():
    print('T53 seams of every order: k mechanisms whose every proper subset passes while the whole fails: k | '
          'signal: coupling where k symmetric loops are singular | relative gain of a pair there | of k - 1 '
          'loops there | 2 (k - 1) / k | assumption: stranded after full failure, the whole cycle of k | the '
          'worst proper subset | order: passes the spread order needs | the worst proper subset in the order '
          'it inherits')
    for k in (3, 4, 5, 6):
        a = singular_coupling(k)
        sub = relative_gains(symmetric_gain(k - 1, a))
        names = ['w%d' % i for i in range(k)]
        needs = {names[i]: {names[(i + 1) % k]} for i in range(k)}
        place = {n: {i} for i, n in enumerate(names)}
        worst_sub = max(len(recover({x: place[x] for x in s}, {x: needs[x] & set(s) for x in s}, set(range(k))))
                        for m in range(1, k) for s in itertools.combinations(names, m))
        ws = typed_chain(('value',) * (k - 1))
        order = spread_order(k)

        def need(members):
            full = admit(pod(), members, passes=len(members) + 2)
            return min(p for p in range(1, len(members) + 3) if admit(pod(), members, passes=p) == full)
        worst_order = max(need([ws[i] for i in order if i in s]) for m in range(1, k) for s in itertools.combinations(range(k), m))
        print('  %d | %.4f | %.4f | %s | %.4f | %d | %d | %d | %d' % (
            k, a, pair_gain_at_singular(k), '%.4f' % sub[0][0], subset_gain(k - 1, a), len(recover(place, needs, set(range(k)))), worst_sub,
            need([ws[i] for i in order]), worst_order))


def t54():
    print('T54 passes an order needs, one plus the most inversions along any path of facts, against simulation '
          '(150 random dependency graphs, 2 to 4 webhooks, 2 to 7 facts, every order of each; seed 7): graphs '
          '| orders | orders needing 1 pass | 2 | 3 | 4 or more | orders where the count and the simulation '
          'disagree')
    rng = random.Random(7)
    graphs = orders = disagree = 0
    needs = [0, 0, 0, 0]
    for _ in range(150):
        writers = ['a', 'b', 'c', 'd'][:rng.randint(2, 4)]
        facts = {}
        for f in range(rng.randint(2, 7)):
            facts['f%d' % f] = (rng.choice(writers), {'f%d' % g for g in range(f) if rng.random() < 0.35})
        hooks = fact_webhooks(facts, writers)
        graphs += 1
        for order in itertools.permutations(writers):
            ordered = [hooks[w] for w in order]
            full = admit(pod(), ordered, passes=len(facts) + 2)
            need = fact_passes(order, facts)
            simulated = min(p for p in range(1, len(facts) + 3) if admit(pod(), ordered, passes=p) == full)
            orders += 1
            needs[min(need, 4) - 1] += 1
            disagree += need != simulated
    print('  %d | %d | %d | %d | %d | %d | %d' % (graphs, orders, needs[0], needs[1], needs[2], needs[3], disagree))


def t55():
    print('T55 the order verdict of the audited cluster under renamings of one configuration (facts: the proxy '
          'container, written by the injector; the proxy pinned, by the digest pin once the container exists; '
          'the signature over the pinned proxy, by the signer once it is pinned): configuration names | order '
          'by name | rank of the proxy pinned | rank of the signature | passes needed against 2 | admitted '
          'object')
    facts = {'proxy container': ('sidecar', set()), 'proxy pinned': ('digest', {'proxy container'}),
             'signature over the pinned proxy': ('signer', {'proxy pinned'})}
    hooks = {'sidecar': sidecar, 'digest': digest, 'signer': signer}
    for signer_name in ('admission-signer', 'signer', 'zz-signer'):
        configs = {signer_name: ['signer'], 'image-digest': ['digest'], 'sidecar-injector': ['sidecar']}
        order = config_order(configs)
        pos = {w: i for i, w in enumerate(order)}
        r1 = int(pos['digest'] < pos['sidecar'])
        r2 = r1 + int(pos['signer'] < pos['digest'])
        admitted = admit(pod(), [hooks[w] for w in order], passes=2)
        fixed = all(w(admitted) == admitted for w in hooks.values())
        print('  %s | %s | %d | %d | %d | %s' % (', '.join(sorted(configs)), ', '.join(order), r1, r2, fact_passes(order, facts),
                                         'a common fixed point' if fixed else 'not a common fixed point'))


def t56():
    print('T56 the order of an interaction, counted in what the seam needs: two webhooks handing facts back '
          'and forth (A writes f1, B writes f2 from f1, A writes f3 from f2, B writes f4 from f3), all '
          'IfNeeded | passes needed in the order A, B | in the order B, A | admitted object under the '
          'contract, order B, A; and the shared state counted in informers (LIST 100 seat-s, capacity 100 '
          'seat-s/s, history 300 s, watch 300 to 600 s) | informers for a second wave | for a storm under any '
          'order of service | for a storm in the idealized queue')
    facts = {'f1': ('A', set()), 'f2': ('B', {'f1'}), 'f3': ('A', {'f2'}), 'f4': ('B', {'f3'})}
    hooks = fact_webhooks(facts)
    ordered = [hooks['B'], hooks['A']]
    full = admit(pod(), ordered, passes=6)
    two = admit(pod(), ordered, passes=2)
    print('  pair | %d | %d | %s' % (fact_passes(('A', 'B'), facts), fact_passes(('B', 'A'), facts),
                                   'a common fixed point' if two == full else 'not a common fixed point'))
    print('  state | %d | %d | %d' % (informers_to_bind(SHORT + RETENTION, SEATS, 100.0), informers_to_bind(MEAN + RETENTION, SEATS, 100.0),
                                     informers_to_bind(MEAN + 2 * RETENTION, SEATS, 100.0)))


def t73():
    print('T73 how often a failure is one no pair shows. Rows "signal": loops | couplings drawn uniform in '
          "[-c, c], unit diagonal, 20000 draws, seed 3 | c | share of systems in which some loop's relative "
          "gain is negative | of those, share in which some pair's relative gain is negative | share in which "
          'every pair reads below 2. Rows "assumption": components | each needs another with probability p, '
          'none matches its own pods, 20000 draws, seed 3 | p | share of graphs a full failure strands | of '
          'those, share with no pair that needs each other. Rows "order": webhooks | random fact graphs as T54 '
          '(n to 8 facts, prerequisite probability 0.35, 3000 graphs, seed 7), every order | orders needing '
          "more than the contract's 2 passes | of those, share in which every pair, in the order it inherits, "
          'needs at most 2 | share in which every proper subset does')
    rng = random.Random(3)
    for n in (3, 4, 5):
        for c in (0.8, 0.95):
            rev = pair_rev = low = 0
            for _ in range(20000):
                g = [[1.0 if i == j else rng.uniform(-c, c) for j in range(n)] for i in range(n)]
                lam = relative_gains(g)
                if any(lam[i][i] < 0 for i in range(n)):
                    rev += 1
                    pairs = [1.0 / (1.0 - g[i][j] * g[j][i]) for i in range(n) for j in range(i + 1, n)]
                    pair_rev += any(x < 0 for x in pairs)
                    low += max(pairs) < 2.0
            print('  signal | %d | %.2f | %.4f | %.4f | %.4f' % (n, c, rev / 20000.0, pair_rev / rev, low / rev))
    for n in (3, 4, 5, 6):
        for p in (0.2, 0.35):
            cyc = miss = 0
            for _ in range(20000):
                g = {a: {b for b in range(n) if b != a and rng.random() < p} for a in range(n)}
                if cyclic_components(g):
                    cyc += 1
                    miss += not any(b in g[a] and a in g[b] for a in range(n) for b in range(a + 1, n))
            print('  assumption | %d | %.2f | %.4f | %.4f' % (n, p, cyc / 20000.0, miss / cyc))
    rng = random.Random(7)
    for nw in (3, 4, 5):
        fail = pair_ok = all_ok = 0
        for _ in range(3000):
            writers = ['a', 'b', 'c', 'd', 'e'][:nw]
            facts = {}
            for f in range(rng.randint(nw, 8)):
                facts['f%d' % f] = (rng.choice(writers), {'f%d' % g for g in range(f) if rng.random() < 0.35})
            for order in itertools.permutations(writers):
                if fact_passes(order, facts) <= 2:
                    continue
                fail += 1

                def ok(sub):
                    return fact_passes([w for w in order if w in sub], subset_facts(facts, set(sub))) <= 2
                pair_ok += all(ok(sub) for sub in itertools.combinations(writers, 2))
                all_ok += all(ok(sub) for m in range(1, nw) for sub in itertools.combinations(writers, m))
        print('  order | %d | %d | %.4f | %.4f' % (nw, fail, pair_ok / fail, all_ok / fail))


def t74():
    print('T74 fixing one seam through a parameter another seam shares: the specimens of Parts 1 and 2 (HPA '
          'and VPA on one deployment, 16 pods, 30x surge, limit = request, 8 pods per node, pod 90 s, node 210 '
          's, no headroom) | fix of the signal seam | HPA target | HPA metric | relative gain of the HPA loop '
          '| rests (rest band at steady load) | rounds a saturated metric needs | seconds until capacity meets '
          'the surge, simulated | closed form, every round waiting | with ample nodes')
    lo, hi = equilibrium_band(q=1.0)
    for label, t in (('none', 0.5), ('target into the band', 0.8), ('target into the band', 0.9)):
        print('  %s | %.2f | CPU utilization | %s | %s | %d | %d | %d | %d' % (
            label, t, 'singular', 'yes' if lo <= t <= hi else 'no', rounds(30, target=t), nested(30, target=t),
            nested_time(30, POD, NODE, target=t), nested(30, target=t, headroom=10 ** 6)))
    print('  %s | %.2f | requests per second per pod, measured on arrival | %.0f | %s | %d | %d | %d | %d' % (
        'metric to load', 0.5, custom_metric_relative_gain(0.0), 'yes', 1, nested(30, metric='load'),
        POD + NODE, nested(30, metric='load', headroom=10 ** 6)))


def t75():
    print('T75 the default priority levels, which keep node heartbeats apart from kubelet lists (apiserver '
          'apis/flowcontrol/bootstrap/default.go: nominal concurrency shares system 30, node-high 40, '
          'leader-election 10, workload-high 40, workload-low 100, global-default 20, catch-all 5; lists by '
          'nodes go to system, their Lease updates to node-high), and the storm onset of T41 in each (2000 '
          'informers, the server 100 seat-s/s in all, wait limit, sudden trigger, no borrowing) | level that '
          "carries the kubelets' lists | its share of the shares | seat-s/s | least list cost at which a storm "
          'is still running in hour 8 (one below has none) | backlog there, s')
    shares = {'catch-all': 5, 'system': 30, 'node-high': 40, 'leader-election': 10, 'workload-high': 40, 'workload-low': 100, 'global-default': 20}
    total = sum(shares.values())
    for label, part in (('the whole server', total), ('system, as configured', shares['system']),
                        ('system and node-high merged', shares['system'] + shares['node-high'])):
        cap = 100.0 * part / total
        def storms(c):
            return relist_limited(float(c), capacity=cap)[0][-1] > 0
        lo, hi = 2, 130
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if storms(mid):
                hi = mid
            else:
                lo = mid
        assert storms(hi) and not storms(hi - 1)
        print('  %s | %d/%d | %.2f | %d | %.0f' % (label, part, total, cap, hi, backlog(hi, CLIENTS, cap)))


def t81():
    print("T81 Part 1's two fixes on Part 2's nested surge (specimen: 8 pods to a node, 90 s pod and 210 s "
          'node, a surge to 30 times the demand the pair rests at): fix | horizontal target | scale-up '
          'tolerance | resting utilization | starting pods | seconds until capacity meets the surge | with '
          'ample nodes')
    v = vpa_utilisation()
    tol = round(stopping_scale_up_tolerance(0.5), 2)
    k = 30 * v / 0.5
    print('  none, drifting | 0.5 | 0.1 | 0.500 | 16 | %d | %d' % (nested(30), nested(30, headroom=10 ** 4)))
    print('  target moved | %.2f | 0.1 | %.3f | 16 | %d | %d' % (round(v, 2), round(v, 2), nested(30, target=round(v, 2)), nested(30, target=round(v, 2), headroom=10 ** 4)))
    for n0 in (16, 9):
        print('  scale-up tolerance | 0.5 | %.2f | %.3f | %d | %d | %d' % (tol, v, n0, nested(k, n0=n0, tol=tol), nested(k, n0=n0, tol=tol, headroom=10 ** 4)))


def t88():

    def wrap(f, never):
        def w(obj):
            return f(obj)
        w.__name__ = f.__name__
        w.never = never
        return w
    print('T88 the audited order seam under the reinvocation policies the survey found (Part 5): the injector, '
          'digest pin and signer of T18, two passes. Rows "audit": injector | pin | signer policies | admitted '
          'object at the names admission-signer, signer, zz-signer, which sort the webhooks '
          'signer/digest/sidecar, digest/sidecar/signer, digest/sidecar/signer')
    for pin, inj, sig in itertools.product((False, True), repeat=3):
        hooks = {'sidecar': wrap(sidecar, inj), 'digest': wrap(digest, pin), 'signer': wrap(signer, sig)}
        cells = []
        for name in ('admission-signer', 'signer', 'zz-signer'):
            order = config_order({name: ['signer'], 'image-digest': ['digest'], 'sidecar-injector': ['sidecar']})
            got = admit(pod(), [hooks[w] for w in order], passes=2)
            cells.append('fixed point' if all(f(got) == got for f in (sidecar, digest, signer)) else 'not fixed')
        print('  audit | %s | %s | %s | %s' % ('Never' if inj else 'IfNeeded', 'Never' if pin else 'IfNeeded', 'Never' if sig else 'IfNeeded', ' | '.join(cells)))
    print('  Rows "prevalence": webhooks | random fact graphs as T73 (n to 8 facts, prerequisite probability 0.35, 1000 graphs, seed 7), every order, each webhook keeping Never with probability q (seed 11), admission simulated over two passes | q | failing (graph, order) cases | of those, share in which every pair, in the order and with the policies it inherits, admits a common fixed point')
    for nw in (3, 4):
        for q in (0.0, 10 / 13):
            rng, prng = random.Random(7), random.Random(11)
            fail = pair_ok = 0
            for _ in range(1000):
                writers = ['a', 'b', 'c', 'd'][:nw]
                facts = {}
                for f in range(rng.randint(nw, 8)):
                    facts['f%d' % f] = (rng.choice(writers), {'f%d' % g for g in range(f) if rng.random() < 0.35})
                never = {w: prng.random() < q for w in writers}

                def converges(order, sub_facts):
                    hs = fact_webhooks(sub_facts, order)
                    got = admit(pod(), [wrap(hs[w], never[w]) for w in order], passes=2)
                    return all(hs[w](got) == got for w in order)
                for order in itertools.permutations(writers):
                    if converges(list(order), facts):
                        continue
                    fail += 1
                    pair_ok += all(converges([w for w in order if w in sub], subset_facts(facts, set(sub))) for sub in itertools.combinations(writers, 2))
            print('  prevalence | %d | %.4f | %d | %.4f' % (nw, q, fail, pair_ok / fail))


def t109():
    print('T109 the cross-seam frontier of Parts 1 and 2 on one deployment (16 pods, limit = request, 8 pods '
          'per node, pod 90 s, node 210 s, a surge to 30 times the demand the pair carries before it): Rows '
          '"target": horizontal target | scale-up tolerance | drift, doublings per 1,000 h at a steady load '
          '(ln F / s*, 0 inside the band) | seconds until capacity meets the surge | utilization before the '
          'surge. Rows "matched": the same with the scale-up tolerance v / target - 1 that rests the pair: '
          'target | tolerance | drift | seconds | utilization before the surge | rounds, ceil(ln(30 v) / '
          'ln(min(1/target, 2))). Row "load": the horizontal loop on load measured on arrival | drift | seconds')
    v = vpa_utilisation()
    lo, hi = equilibrium_band(q=1.0)
    for u in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9):
        f = step_factor(u)
        rate = 0.0 if u >= lo else 1000.0 * math.log(f) / step_interval() / math.log(2)
        print('  target | %.2f | 0.10 | %.2f | %d | %.3f' % (u, rate, nested(30, target=u), u))
    for u in (0.3, 0.4, 0.5, 0.55, 0.6, 0.7, 0.8):
        tol = matched_tolerance(u)
        print('  matched | %.2f | %.3f | 0.00 | %d | %.3f | %d' % (u, tol, nested(30 * v / u, target=u, tol=tol), v, resting_rounds(30, u)))
    print('  load | 0.00 | %d' % nested(30, metric='load'))


def _onset_at(part):
    total = 245
    cap = 100.0 * part / total
    def storms(c):
        return relist_limited(float(c), capacity=cap)[0][-1] > 0
    lo, hi = 2, 130
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if storms(mid):
            hi = mid
        else:
            lo = mid
    return part, cap, hi


def t110():
    print("T110 the storm onset against the list level's share of the server (2000 informers, the whole server "
          '100 seat-s/s, wait limit, sudden trigger, no borrowing): Rows: shares of 245 | seat-s/s | least '
          'list cost at which a storm is still running in hour 8 | backlog there, s | the onset backlog of the '
          'whole server scaled to the share, 2260 x share / 245 x 100 / 2000')
    parts = (15, 30, 50, 70, 100, 150, 200, 245)
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(_onset_at, parts))
    for part, cap, hi in res:
        print('  %d | %.2f | %d | %.0f | %.1f' % (part, cap, hi, backlog(hi, CLIENTS, cap), 2260.0 * cap / CLIENTS))


def t111():
    print('T111 the order of each seam: the size of the smallest set of mechanisms its test fails, which every '
          'check of fewer passes. Rows "signal": system | order (smallest principal submatrix, rows scaled to '
          'unit self-gain, with a non-positive determinant). Rows "signal-random": loops | couplings uniform '
          'in [-0.8, 0.8], 20000 draws, seed 3 | systems the test fails on as a whole | of those, share of '
          'order 2, 3, ... up to the loops. Rows "assumption": system | girth of the start-time graph. Rows '
          '"assumption-random": 1,000 components | weights | mean needs per component | girth, seeds 0 to 2. '
          'Rows "order": system | order. Rows "order-random": webhooks | random fact graphs as T73, every '
          'order needing more than 2 passes | count | share of order 2, 3, ... Row "signal-whole-passes": a '
          'system the whole-system test passes while every pair fails. Rows "state": informers | list costs | '
          'order, the fewest heaviest informers whose summed list work passes capacity x (mean watch + '
          'history), median and 10th percentile of 200 draws, seed 9')
    print('  signal | two autoscalers on one CPU metric | %d' % signal_order([[-1.0, -1.0], [-1.0, -1.0]]))
    print('  signal | split pairing, Parallel collector (beta 1.28), live set following load, heap growing into its limit (xi 0.6) | %d' % signal_order(split_gain_matrix(1.28, 1.0, 1.0, 0.6)))
    print('  signal | split pairing, beta theta 0.55 | %s' % signal_order([[-1.0, -0.55], [-1.0, -1.0]]))
    for n in (3, 6):
        print('  signal | %d symmetric loops at coupling -1/(n-1) | %d' % (n, signal_order(symmetric_gain(n, singular_coupling(n)))))
    rng = random.Random(3)
    for n in (3, 4, 5):
        orders = []
        for _ in range(20000):
            g = [[1.0 if i == j else rng.uniform(-0.8, 0.8) for j in range(n)] for i in range(n)]
            k = signal_order(g)
            if k is not None:
                orders.append(k)
        print('  signal-random | %d | %d | %s' % (n, len(orders), ' | '.join('%d: %.4f' % (k, orders.count(k) / len(orders)) for k in range(2, n + 1))))
    print('  assumption | surveyed defaults (T89) | %s' % assumption_order(default_start_graph(SURVEY_DEFAULTS)))
    for label, exponent in (('equal', None), ('Pareto 1.8', 1.8)):
        for c in (0.5, 1.0, 2.0):
            gs = []
            for sd in (0, 1, 2):
                r2 = random.Random(sd)
                w = [1.0] * 1000 if exponent is None else pareto_weights(1000, exponent, r2)
                gs.append(assumption_order(gen_needs(c, w, r2)))
            print('  assumption-random | %s | %.1f | %s' % (label, c, ', '.join(str(x) for x in gs)))
    print('  order | audited chain signer, digest pin, injector (names admission-signer, image-digest, sidecar-injector) | %d' % order_order(
        ['signer', 'digest', 'sidecar'], {'sidecar': ('sidecar', set()), 'pin': ('digest', {'sidecar'}), 'sign': ('signer', {'pin'})}))
    rng = random.Random(7)
    for nw in (3, 4, 5):
        writers = ['w%d' % i for i in range(nw)]
        orders = []
        for _ in range(3000):
            facts = {}
            for f in range(rng.randint(nw, 8)):
                facts['f%d' % f] = (rng.choice(writers), {'f%d' % g for g in range(f) if rng.random() < 0.35})
            for order in itertools.permutations(writers):
                if fact_passes(order, facts) > 2:
                    orders.append(order_order(list(order), facts))
        print('  order-random | %d | %d | %s' % (nw, len(orders), ' | '.join('%d: %.4f' % (k, orders.count(k) / len(orders)) for k in range(2, nw + 1))))
    print('  state | 2000 | 100 seat-seconds each | %d' % state_order([100.0] * 2000, 100.0, 450.0, 300.0))
    rng = random.Random(9)
    for alpha in (3.0, 1.5, 1.2):
        ks = sorted(state_order(pareto_costs(2000, alpha, 112.5, rng), 100.0, 450.0, 300.0) or 2001 for _ in range(200))
        print('  state | 2000 | Pareto %.1f, mean 112.5 | median %d, 10th percentile %d' % (alpha, ks[100], ks[20]))
    row = [1.0, 2.0, 2.0, -2.0]
    g = [[row[(j - i) % 4] for j in range(4)] for i in range(4)]

    def verdicts(k):
        return ', '.join('%s %s' % ('-'.join(str(x + 1) for x in sub), 'passes' if signal_set_passes(g, sub) else 'fails')
                         for sub in itertools.combinations(range(4), k))
    print('  signal-whole-passes | 4 loops, circulant with first row (1, 2, 2, -2) | whole: determinant %.0f, relative '
          'gains %s, passes %s | triples: %s | pairs: %s' % (
              determinant(g), ', '.join('%.3f' % relative_gains(g)[k][k] for k in range(4)), signal_set_passes(g, range(4)),
              verdicts(3), verdicts(2)))
    w = [[1.0, 1.5, 1.0], [1.5, 1.0, -2.0], [1.5, -1.0, 1.0]]
    print('  signal-negative-determinant | 3 loops, rows (1, 1.5, 1), (1.5, 1, -2), (1.5, -1, 1) | determinant %.2f, '
          'relative gains %s, passes %s' % (determinant(w), ', '.join('%.3f' % relative_gains(w)[k][k] for k in range(3)),
                                            signal_set_passes(w, [0, 1, 2])))
    print('  signal-negative-determinant | 4 symmetric loops at coupling -0.55 | determinant %.4f, relative gain %.3f, '
          'passes %s' % (determinant(symmetric_gain(4, -0.55)), relative_gains(symmetric_gain(4, -0.55))[0][0],
                         signal_set_passes(symmetric_gain(4, -0.55), range(4))))


def t112():
    print("T112 each seam's ratio of what the composite asks to what its contract gives, binding above one "
          '(the assumption at one), and a test cluster at a tenth of the scale. Rows "signal": target | ratio, '
          'the larger of v/((1+tol) u_h) and u_h (1-tol)/v, margin 0.15, tolerance 0.1. Rows "time": free '
          'slots held for 16 running pods | rounds covered | ratio R/(m+1) for a thirtyfold surge. Rows '
          '"state": informers | list cost | ratio N cost/(capacity (mean watch + history)), capacity 100, 450 '
          '+ 300 s. Rows "order": chain | passes | ratio over two passes. Rows "assumption": graph | spectral '
          'radius of the start-time graph. Rows "assumption-random": 1,000 components, seed 0 | weights | mean '
          'needs | spectral radius | E[k_in k_out]/E[k] | components stranded. Rows "tenth": seam | full scale '
          '| a tenth of the scale (signal: doubling hours from 10 replicas and from 1; time: seconds to '
          'capacity, 16 and 160 pods, headroom in proportion and fixed; state: LISTs completed in hours 2 to 4 '
          'after a full trigger, with capacity kept and capacity scaled)')
    for u_h in (0.3, 0.5, 0.7, 0.8, 0.9, 0.95):
        print('  signal | %.2f | %.3f' % (u_h, signal_ratio(u_h)))
    for h in (0, 16, 48, 112):
        m = covered_rounds(h, 16, 30)
        print('  time | %d | %d | %.3f' % (h, m, time_ratio(30, m)))
    for n, cost in ((2000, 100.0), (2000, 120.0), (750, 100.0), (601, 100.0)):
        print('  state | %d | %.0f | %.3f' % (n, cost, state_ratio(n, cost, 100.0, 450.0, 300.0)))
    print('  order | audited chain | 3 | %.2f' % order_ratio(3))
    print('  order | renamed into chain order, every webhook reinvoked | 1 | %.2f' % order_ratio(1))
    print('  assumption | surveyed defaults (T89) | %.3f' % assumption_ratio(default_start_graph(SURVEY_DEFAULTS)))
    comps = dict(SURVEY_DEFAULTS)
    comps['kyverno'] = dict(comps['kyverno'], fail_closed=False)
    print('  assumption | Kyverno failing open | %.3f' % assumption_ratio(default_start_graph(comps)))
    for label, exponent in (('equal', None), ('Pareto 1.8', 1.8)):
        for c in (0.5, 1.0, 1.2, 1.5, 2.0):
            rng = random.Random(0)
            w = [1.0] * 1000 if exponent is None else pareto_weights(1000, exponent, rng)
            needs = gen_needs(c, w, rng)
            k_in = {i: 0 for i in needs}
            for i in needs:
                for j in needs[i]:
                    k_in[j] += 1
            mean = sum(len(v) for v in needs.values()) / 1000.0
            prod = sum(k_in[i] * len(needs[i]) for i in needs) / 1000.0
            print('  assumption-random | %s | %.1f | %.3f | %.3f | %d' % (label, c, assumption_ratio(needs), prod / mean, len(stranded(needs))))
    print('  tenth | signal, target 0.5 | %.2f | %.2f' % (hpa_vpa.simulate(0.5, demand=100.0, replicas=10, days=40)[1],
                                                         hpa_vpa.simulate(0.5, demand=10.0, replicas=1, days=40)[1]))
    print('  tenth | time, no headroom | %d | %d' % (nested(30, n0=160), nested(30, n0=16)))
    print('  tenth | time, headroom 1 pod in 1 | %d | %d' % (nested(30, n0=160, headroom=160), nested(30, n0=16, headroom=16)))
    print('  tenth | time, headroom 16 slots at both | %d | %d' % (nested(30, n0=160, headroom=16), nested(30, n0=16, headroom=16)))
    full = relist.simulate_limited(120.0, clients=2000, capacity=100.0, hours=4)[0]
    kept = relist.simulate_limited(120.0, clients=200, capacity=100.0, hours=4)[0]
    scaled = relist.simulate_limited(120.0, clients=200, capacity=10.0, hours=4)[0]
    grown = relist.simulate_limited(12.0, clients=200, capacity=1.0, hours=4)[0]
    print('  tenth | state, list cost 120, 2000 informers and 200, capacity kept | %s | %s' % (full[1:], kept[1:]))
    print('  tenth | state, list cost 120, 2000 informers and 200, capacity a tenth | %s | %s' % (full[1:], scaled[1:]))
    print('  tenth | state, lists that grow with the cluster (cost 12), 2000 informers and 200, capacity a hundredth | %s | %s' % (full[1:], grown[1:]))


def t115():
    print('T115 whole-system tests on incomplete descriptions: a share of the description dropped at random, '
          'as an inventory that missed it would. Rows "assumption": 30 components, equal weights, seeds 0 to '
          '299 | mean needs | share of needs dropped | graphs with a cycle | share of them judged acyclic from '
          'the incomplete description | graphs judged cyclic that are not (always 0). Rows "assumption-1000": '
          '1,000 components, mean needs 1.5, seed 0 | share dropped | components stranded by the complete '
          'description | by the incomplete one. Rows "order": random fact graphs of T111 with 4 webhooks, '
          '1,500 draws, seed 7 | share of prerequisites dropped | orders needing more than 2 passes | share of '
          'them judged to converge | orders judged to fail that converge (always 0). Rows "signal": loops | '
          'couplings uniform in [-0.8, 0.8], one coupling set to zero, 20000 draws, seed 3 | failing systems | '
          'share judged to pass | passing systems | share judged to fail. Row "state": list cost at which the '
          'ratio of 2000 informers passes one, capacity 100, 450 + 300 s. Rows "example": the two systems of '
          'Proposition 40(b) | complete or with the coupling left out | determinant | relative gains | verdict')
    for c in (0.8, 1.0, 1.5):
        for share in (0.05, 0.2):
            fails = flips = false = 0
            for sd in range(300):
                rng = random.Random(sd)
                needs = gen_needs(c, [1.0] * 30, rng)
                part = omit_needs(needs, share, rng)
                cyc, pcyc = bool(cyclic_components(needs)), bool(cyclic_components(part))
                fails += cyc
                flips += cyc and not pcyc
                false += pcyc and not cyc
            print('  assumption | %.1f | %.2f | %d | %.3f | %d' % (c, share, fails, flips / fails, false))
    needs = gen_needs(1.5, [1.0] * 1000, random.Random(0))
    for share in (0.05, 0.1, 0.2):
        print('  assumption-1000 | %.2f | %d | %d' % (share, len(stranded(needs)), len(stranded(omit_needs(needs, share, random.Random(1))))))
    for share in (0.1, 0.3):
        rng = random.Random(7)
        fails = flips = false = 0
        for _ in range(1500):
            writers, facts = random_facts(4, rng)
            part = omit_prereqs(facts, share, rng)
            for order in itertools.permutations(writers):
                a, b = fact_passes(order, facts) > 2, fact_passes(order, part) > 2
                fails += a
                flips += a and not b
                false += b and not a
        print('  order | %.1f | %d | %.3f | %d' % (share, fails, flips / fails, false))
    for loops in (3, 4, 5):
        out = signal_flips(loops, 20000, random.Random(3))
        passes = 20000 - out['fails']
        print('  signal | %d | %d | %.3f | %d | %.4f' % (loops, out['fails'], out['fail_to_pass'] / out['fails'], passes, out['pass_to_fail'] / passes))
    lo, hi = 0.0, 1000.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        lo, hi = (lo, mid) if state_ratio(2000, mid, 100.0, 450.0, 300.0) > 1.0 else (mid, hi)
    print('  state | %.1f' % hi)
    sym = [[1.0, -0.5, -0.5], [-0.5, 1.0, -0.5], [-0.5, -0.5, 1.0]]
    mixed = [[1.0, -0.8, -0.8], [-0.8, 1.0, 0.0], [-0.8, 0.8, 1.0]]
    for label, g, (i, j) in (('three symmetric loops at -0.5', sym, (0, 1)), ('loop 3 coupled to loop 2 at +0.8', mixed, (2, 1))):
        h = [row[:] for row in g]
        h[i][j] = 0.0
        for which, m in (('complete', g), ('coupling %d-%d left out' % (i + 1, j + 1), h)):
            d = determinant(m)
            gains = 'singular' if abs(d) < 1e-12 else ', '.join('%.3f' % relative_gains(m)[k][k] for k in range(3))
            print('  example | %s | %s | %.3f | %s | %s' % (label, which, d, gains, 'pass' if signal_set_passes(m, [0, 1, 2]) else 'fail'))


def t116():
    print('T116 the assumption x order frontier at the surveyed defaults (T89): four settings of Kyverno and '
          'Consul, each run through a full restart of the fifteen components. variant | components still down '
          '| namespaces whose pods Kyverno never pins (its exclusions) | namespaces whose pods Consul never '
          'injects (its exclusions) | pods admitted while Kyverno is down')
    def run(label, comps):
        needs = default_start_graph(comps)
        down = recover({c: {c} for c in comps}, needs, set(comps))
        ky, co = comps['kyverno'], comps['consul']
        print('  %s | %d of %d | %s | %s | %s' % (label, len(down), len(comps), ', '.join(sorted(ky['excludes'])),
                                                ', '.join(sorted(co['excludes'])), 'all, unpinned' if not ky['fail_closed'] else 'none'))
    run('defaults', SURVEY_DEFAULTS)
    comps = dict(SURVEY_DEFAULTS)
    comps['consul'] = dict(comps['consul'], excludes=comps['consul']['excludes'] | {'kyverno'})
    run('Consul excluding the kyverno namespace', comps)
    comps = dict(SURVEY_DEFAULTS)
    comps['kyverno'] = dict(comps['kyverno'], excludes=comps['kyverno']['excludes'] | {'consul'})
    run('Kyverno excluding the consul namespace', comps)
    comps = dict(SURVEY_DEFAULTS)
    comps['kyverno'] = dict(comps['kyverno'], fail_closed=False)
    run('Kyverno with forceFailurePolicyIgnore', comps)


def t117():
    print('T117 a whole-system supervisor on the signal and time-scale seams of one deployment (16 pods, limit '
          '= request, 8 pods per node, pod 90 s, node 210 s, a surge to 30 times the demand the pair carries). '
          'Rows "greedy": seams in order of their ratios, each given the smallest one-setting change that '
          'brings its own ratio to one, taken again when a later fix pushes it back: step | fix | target | '
          'free slots held | signal ratio | time ratio | seconds to meet the surge. Rows "joint": each fix of '
          'the signal seam with the fewest slots that bring both ratios to one, the choice first: fix | target '
          '| free slots | signal ratio | time ratio | seconds')
    for i, s in enumerate(greedy()):
        print('  greedy | %d | %s | %.2f | %d | %.3f | %.3f | %d' % (i, s['fix'], s['target'], s['slots'], s['signal_ratio'], s['time_ratio'], s['surge_s']))
    for allow in (True, False):
        b = joint(allow_load=allow)
        print('  joint | %s | %.2f | %d | %.3f | %.3f | %d' % (b['fix'], b['target'], b['slots'], b['signal_ratio'], b['time_ratio'], b['surge_s']))
