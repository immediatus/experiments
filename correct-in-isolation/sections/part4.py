"""Sections of Part 4, a shared assumption: T13, T14, T47, T48, T49, T58, T59, T60, T61, T62, T63, T64, T80, T89, T100, T101, T114."""
import math
import random
from concurrent.futures import ProcessPoolExecutor

from audit import (
    SURVEY_DEFAULTS,
    cyclic_components,
    default_start_graph,
    merge_restart_counts,
    min_feedback_vertex_set,
    restart_counts_range,
    weigh_restart_counts,
)
from formulas import app_loss_distribution, bind_probability, cold_start_chain, cycle_mean_time_to_bind, rejection_life, stalled_rollout
from percolation import gen_needs, greedy_relaxation, hard_floor, pareto_weights, predicted_threshold, residual_hidden, stranded
from recovery import drain_order_losses, eviction_regime, heartbeat_unknown, placed_drain, recover, rolling_drain, simulated_life, simulated_time_to_bind


def t47():
    print('T47 a rolling node upgrade, every node drained once in order (9 nodes; webhook on nodes 0, 3, 6, '
          'DNS on 1, 4, app on 2, 5, 8): configuration | webhook replicas after | app replicas after | drain '
          'stalled at node')
    place = {'webhook': [0, 3, 6], 'dns': [1, 4], 'app': [2, 5, 8]}
    cases = (('documented practice: the webhook excludes its own namespace', {'app': {'webhook'}}, {}, None),
             ('availability edge: failurePolicy Fail, the webhook must be up to admit its own pods', {'app': {'webhook'}, 'webhook': {'webhook'}}, {}, None),
             ('rejection edge: the running webhook rejects its own pods, failurePolicy Fail', {'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}}, None),
             ('rejection edge, failurePolicy Ignore', {}, {'webhook': {'webhook'}}, None),
             ('rejection edge, failurePolicy Fail, disruption budget minAvailable 2', {'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}}, {'webhook': 2}),
             ('rejection edge, failurePolicy Fail, disruption budget minAvailable 1', {'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}}, {'webhook': 1}))
    for name, needs, rejects, budget in cases:
        out = rolling_drain(place, needs, rejects, list(range(9)), budget)
        print('  %s | %d | %d | %s' % (name, out['replicas']['webhook'], out['replicas']['app'], '-' if out['stalled'] is None else out['stalled']))


def t48():
    print('T48 the life of a webhook that rejects its own pods, node failures independent, a lost replica '
          'never replaced: replicas | node mean time between failures, days | expected life, days, closed | '
          'simulated, 20000 draws')
    for mtbf in (30.0, 90.0):
        for n in (1, 2, 3, 5):
            print('  %d | %.0f | %.1f | %.1f' % (n, mtbf, rejection_life(n, mtbf), simulated_life(n, mtbf)))


def t49():
    print('T49 application replicas lost to one rolling drain, over drain orders (webhook rejects its own '
          'pods, failurePolicy Fail; 3 webhook and 3 application replicas, each on its own node; 20000 random '
          'orders): replicas lost | probability, closed | share of orders')
    place = {'webhook': [0, 3, 6], 'dns': [1, 4], 'app': [2, 5, 8]}
    closed = app_loss_distribution(3, 3)
    sim = drain_order_losses(place, {'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}}, orders=20000)
    for j in range(4):
        print('  %d | %.3f | %.3f' % (j, closed[j], sim.get(j, 0) / 20000))


ZONES = [{0, 1, 2}, {3, 4, 5}, {6, 7, 8}]   # trace input, Part 4: 9 nodes in 3 zones


def _configs():
    """Start-time edges of three admission configurations, each a documented warning or its fix."""
    return (('documented practice: webhook excludes its own namespace and kube-system', {'app': {'webhook'}}),
            ('webhook matches its own pods', {'app': {'webhook'}, 'webhook': {'webhook'}}),
            ('webhook matches kube-system and resolves a dependency through cluster DNS',
             {'app': {'webhook'}, 'dns': {'webhook'}, 'webhook': {'dns'}}))


def t13():
    print('T13 share of failures after which something never comes back (9 nodes, 3 zones; DNS 2 replicas, app '
          '3): configuration | webhook placement | one node | one zone | two zones | all nodes')
    placements = (('one replica per zone', {0, 3, 6}), ('three replicas in one zone', {0, 1, 2}))
    for name, needs in _configs():
        for where, nodes in placements:
            place = {'webhook': nodes, 'dns': {1, 4}, 'app': {2, 5, 8}}
            row = []
            for failures in ([{n} for n in range(9)], ZONES,
                             [a | b for a, b in ((ZONES[0], ZONES[1]), (ZONES[0], ZONES[2]), (ZONES[1], ZONES[2]))],
                             [set(range(9))]):
                row.append('%.2f' % (sum(bool(recover(place, needs, f)) for f in failures) / len(failures)))
            print('  %s | %s | %s' % (name, where, ' | '.join(row)))


def t14():
    print('T14 probability that k random node failures cover a start-time cycle on u distinct nodes: nodes | u | k | probability')
    for n, ks in ((9, (1, 3, 5, 7, 9)), (100, (10, 30, 50, 90, 100))):
        for u in (1, 3, 6):
            for k in ks:
                print('  %d | %d | %d | %.6f' % (n, u, k, bind_probability(n, u, k)))


def t58():
    print('T58 where the scheduler puts replacements during a rolling drain (as T49: webhook rejects its own '
          'pods, failurePolicy Fail; webhook on nodes 0, 3, 6, DNS on 1, 4, app on 2, 5, 8; 20000 random drain '
          'orders, seed 1): placement | app replicas lost 0 | 1 | 2 | 3 (share of orders) | mean lost | mean '
          'evictions per drain')
    place = {'webhook': [0, 3, 6], 'dns': [1, 4], 'app': [2, 5, 8]}
    needs, rejects = {'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}}
    for label, policy, extra in (('out of reach of later drains (T49)', 'out of reach', 0), ('spread, the scheduler default (LeastAllocated)', 'spread', 0),
                                 ('packed (MostAllocated)', 'pack', 0), ('spread, with one empty surge node never drained', 'spread', 1),
                                 ('packed, with one empty surge node never drained', 'pack', 1)):
        rng = random.Random(1)
        lost, evictions = [0, 0, 0, 0], 0
        for _ in range(20000):
            order = list(range(9))
            rng.shuffle(order)
            out = placed_drain(place, needs, rejects, order, None, policy=policy, nodes=9 + extra)
            lost[3 - out['replicas']['app']] += 1
            evictions += out['evictions']
        print('  %s | %s | %.3f | %.2f' % (label, ' | '.join('%.3f' % (x / 20000) for x in lost),
                                         math.fsum(j * x for j, x in enumerate(lost)) / 20000, evictions / 20000))


def t59():
    print('T59 the documented remedy for a stuck eviction applied to the drain of T47 (rejection edge, '
          'failurePolicy Fail, nodes drained in order 0 to 8): disruption budget | stalls at node without the '
          'remedy | nodes where the operator deletes the pod directly | webhook replicas after | app replicas '
          'after')
    place = {'webhook': [0, 3, 6], 'dns': [1, 4], 'app': [2, 5, 8]}
    needs, rejects = {'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}}
    for budget in (2, 1):
        stuck = rolling_drain(place, needs, rejects, list(range(9)), {'webhook': budget})
        out = rolling_drain(place, needs, rejects, list(range(9)), {'webhook': budget}, bypass=True)
        print('  minAvailable %d | %s | %s | %d | %d' % (budget, stuck['stalled'], ', '.join(map(str, out['bypassed'])),
                                                   out['replicas']['webhook'], out['replicas']['app']))
    none = rolling_drain(place, needs, rejects, list(range(9)))
    print('  no budget | - | - | %d | %d' % (none['replicas']['webhook'], none['replicas']['app']))


def t60():
    print('T60 a full restart through two documented backoffs (DNS ready at the time given; the webhook needs '
          'DNS and crashes until it answers, first start 30 s, crash after 5 s, kubelet restarts after 10, 20, '
          '40 s capped at 300 s, ready 10 s after a good start; the application needs the webhook to admit its '
          'pods, failurePolicy Fail, its ReplicaSet retrying on the workqueue backoff 5 ms doubling capped at '
          '1000 s; its pod ready 90 s after admission; DNS ready every 15 s from 30 to 1200): DNS ready s | '
          'webhook ready, instant retries | with the backoff | application ready, instant retries | with both '
          'backoffs | ratio')
    for dns in range(30, 1201, 15):
        out = cold_start_chain(float(dns))
        print('  %d | %.1f | %.1f | %.1f | %.1f | %.2f' % (dns, out['webhook_ready_ideal'], out['webhook_ready'], out['app_ready_ideal'],
                                                       out['app_ready'], out['app_ready'] / out['app_ready_ideal']))


def t61():
    print('T61 how long until a webhook that must admit its own replacements binds, node failures independent '
          '(a lost replica is down for the 300 s toleration plus a 90 s restart, 390 s, then returns on '
          'another node if any replica is up): replicas | node mean time between failures, days | mean time to '
          'bind, days, leading term 1 / (Z lam (lam w)^(Z - 1)) | in years. Rows "check": the same at '
          'accelerated rates (node mean 30, window in the units given), leading term against 4000 seeded '
          'simulations')
    w = 390.0 / 86400.0
    for z in (1, 2, 3):
        for mtbf in (30.0, 90.0):
            days = cycle_mean_time_to_bind(z, mtbf, w)
            print('  %d | %.0f | %.4g | %.4g' % (z, mtbf, days, days / 365.25))
    for z, win in ((2, 1.0), (2, 0.3), (3, 1.0), (3, 2.0)):
        print('  check %d | window %g | %.1f | %.1f' % (z, win, cycle_mean_time_to_bind(z, 30.0, win), simulated_time_to_bind(z, 30.0, win, runs=4000)))


def t62():
    print('T62 a validating webhook with failurePolicy Fail that matches Lease updates, failing each call with '
          'probability q (kubelet renews every 10 s, retries from 0.2 s doubling to 7 s; a node is Unknown '
          'after 50 s without a renewal; its pods are evicted after 300 s Unknown; 100 nodes in one zone; 200 '
          'simulated hours per node): q | renewal attempts before a node turns Unknown | share of time a node '
          'is Unknown | Unknown spells of 300 s or more per node-hour | node controller regime | nodes evicted '
          'per hour, at most')
    for q in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0):
        r = heartbeat_unknown(q, hours=200)
        share = 1.0 if q == 1.0 else r['unknown_share']
        regime = 'every node unhealthy: no evictions' if share >= 1.0 else ('reduced: 0.01 nodes per second' if share >= 0.55 else 'normal: 0.1 nodes per second')
        evicted = eviction_regime(share, 100, r['long_spells_per_hour'] * 100)
        print('  %.2f | %d | %.4f | %.3f | %s | %.1f' % (q, r['attempts_per_grace'], share, r['long_spells_per_hour'], regime, evicted))


def t63():
    print('T63 a webhook that rejects its own pods rolls out a new version of itself under the Deployment '
          'defaults (maxUnavailable 25% rounded down, maxSurge 25% rounded up): replicas | left running when '
          'the rollout stalls | lost for good | new pods the controller asks for, all rejected | expected life '
          'before, days, node failures every 30 days | after')
    for n in (2, 3, 4, 5, 6, 8, 10):
        r = stalled_rollout(n)
        print('  %d | %d | %d | %d | %.1f | %.1f' % (n, r['old'], n - r['old'], r['new_desired'], rejection_life(n, 30.0), rejection_life(r['old'], 30.0)))


def t64():
    print('T64 webhooks with failurePolicy Fail that each exclude their own namespace, as Kyverno and '
          "Gatekeeper do by default; a webhook matches another's pods with probability p (1: rules over every "
          'namespace). Rows: webhooks k | p | share of clusters with a start-time cycle | stranded after a '
          'full restart, mean | fewest exclusions that leave no cycle (minimum feedback arc set), mean | '
          'fewest webhooks switched to Ignore (minimum feedback vertex set), mean; exact, every graph weighted '
          'by its probability')
    for k in (2, 3, 4, 5):
        total = 1 << (k * (k - 1))
        step = max(1, total // 64)
        parts = [(k, lo, min(total, lo + step)) for lo in range(0, total, step)]
        with ProcessPoolExecutor() as ex:
            counts = merge_restart_counts(ex.map(_restart_part, parts))
        for p in (1.0, 0.5, 0.25):
            s = weigh_restart_counts(counts, k, p)
            print('  %d | %.2f | %.3f | %.2f | %.2f | %.2f' % (k, p, s['cyclic'], s['stranded'], s['arcs'], s['vertices']))


def _restart_part(job):
    """The integer tallies of one range of graphs, for the process pool."""
    k, lo, hi = job
    return restart_counts_range(k, lo, hi)

def t80():
    print('T80 the cold start of T60 with the kubelet restart delay reconfigured (KubeletCrashLoopBackOffMax, '
          'beta and on by default since Kubernetes 1.35, a per-node maxContainerRestartPeriod of 1 s to 300 s; '
          'ReduceDefaultCrashLoopBackOffDecay, alpha, 1 s doubling to 60 s), DNS ready every 15 s from 30 to '
          '1200: setting | first delay s | cap s | worst application ratio to instant retries | mean ratio | '
          'worst webhook lateness after a good start was possible, s | DNS times, of 79, at which the webhook '
          'is ready later than with the default')
    times = [float(d) for d in range(30, 1201, 15)]
    default = [cold_start_chain(d) for d in times]
    for label, base, cap in (('default', 10.0, 300.0), ('max 120', 10.0, 120.0), ('max 60', 10.0, 60.0), ('max 30', 10.0, 30.0), ('reduced decay', 1.0, 60.0)):
        out = [cold_start_chain(d, base=base, cap=cap) for d in times]
        ratios = [o['app_ready'] / o['app_ready_ideal'] for o in out]
        late = max(o['webhook_ready'] - o['webhook_ready_ideal'] for o in out)
        worse = sum(o['webhook_ready'] > d0['webhook_ready'] for o, d0 in zip(out, default))
        print('  %s | %g | %g | %.2f | %.3f | %.0f | %d' % (label, base, cap, max(ratios), math.fsum(ratios) / len(ratios), late, worse))


def t89():
    print('T89 the start-time graph of the surveyed projects at their shipped defaults, each in its own '
          'namespace (the AWS Load Balancer Controller and the vertical autoscaler in kube-system, as their '
          'installation guides place them), Kyverno with a policy on Pods; a full restart fails every node: '
          'variant | start-time cycles | components still down after the restart, of 15')
    def run(label, comps):
        needs = default_start_graph(comps)
        cyc = cyclic_components(needs)
        down = recover({c: {c} for c in comps}, needs, set(comps))
        print('  %s | %s | %d of %d: %s' % (label, '; '.join(', '.join(sorted(c)) for c in cyc) or 'none', len(down), len(comps), ', '.join(sorted(down)) or '-'))
    run('defaults', SURVEY_DEFAULTS)
    run('without Consul', {k: v for k, v in SURVEY_DEFAULTS.items() if k != 'consul'})
    run('without Kyverno', {k: v for k, v in SURVEY_DEFAULTS.items() if k != 'kyverno'})
    comps = dict(SURVEY_DEFAULTS)
    comps['consul'] = dict(comps['consul'], excludes=comps['consul']['excludes'] | {'kyverno'})
    run('Consul excluding the kyverno namespace', comps)
    comps = dict(SURVEY_DEFAULTS)
    comps['kyverno'] = dict(comps['kyverno'], fail_closed=False)
    run('Kyverno with forceFailurePolicyIgnore', comps)


def t100():
    print('T100 random start-time graphs of 1,000 components, an edge i -> j (i needs j) with probability '
          'min(1, c w_i w_j / (n E[w]^2)); weights equal (independent degrees), or Pareto with exponent 2.5 or '
          '1.8 (hubs whose in- and out-degrees grow together); a full restart. Rows "share": weights | mean '
          'degree c | share of components stranded, mean of seeds 0 to 29. Rows "threshold": weights | E[w]^2 / '
          'E[w^2] of the drawn weights, mean of seeds 0 to 29')
    for label, exponent in (('equal', None), ('Pareto 2.5', 2.5), ('Pareto 1.8', 1.8)):
        ths = []
        for c in (0.2, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0):
            out = 0
            for seed in range(30):
                rng = random.Random(seed)
                w = [1.0] * 1000 if exponent is None else pareto_weights(1000, exponent, rng)
                if c == 0.2:
                    ths.append(predicted_threshold(w))
                out += len(stranded(gen_needs(c, w, rng)))
            print('  share | %s | %.1f | %.3f' % (label, c, out / 30000.0))
        print('  threshold | %s | %.3f' % (label, math.fsum(ths) / 30))


def t101():
    print('T101 a recovery controller that relaxes the in-edges of components chosen greedily from the largest '
          'cycle core until none is left (1,000 components, seed 0). Rows "relax": weights | mean degree | '
          'components stranded without it | components it relaxes. Rows "hidden": weights | mean degree | '
          'share of edges the controller cannot see | components still stranded. Rows "hard": weights | mean '
          'degree | share of edges that cannot be relaxed | components stranded whatever it relaxes. Row '
          '"survey": components the smallest relaxation of the surveyed defaults (T89) relaxes')
    graphs = {}
    for label, exponent in (('equal', None), ('Pareto 1.8', 1.8)):
        for c in (0.8, 1.2, 1.5, 2.0):
            rng = random.Random(0)
            w = [1.0] * 1000 if exponent is None else pareto_weights(1000, exponent, rng)
            needs = gen_needs(c, w, rng)
            graphs[(label, c)] = needs
            print('  relax | %s | %.1f | %d | %d' % (label, c, len(stranded(needs)), len(greedy_relaxation(needs))))
    for label in ('equal', 'Pareto 1.8'):
        for h in (0.0, 0.05, 0.1, 0.2):
            print('  hidden | %s | 2.0 | %.2f | %d' % (label, h, residual_hidden(graphs[(label, 2.0)], h, random.Random(5))))
        for u in (0.1, 0.2, 0.3, 0.5):
            print('  hard | %s | 2.0 | %.1f | %d' % (label, u, hard_floor(graphs[(label, 2.0)], u, random.Random(7))))
    fvs = min_feedback_vertex_set(default_start_graph(SURVEY_DEFAULTS))
    print('  survey | %d: %s' % (len(fvs), ', '.join(sorted(fvs))))


def t114():
    print('T114 the heartbeat of T62 with failed calls that take time: a webhook that hangs fails each renewal '
          'only at its timeout, and the backoff starts then; one node, 200 hours, seed 1. Rows "attempts": '
          'seconds a failed call takes | attempts after a success that start in time to renew within the 50 s '
          'grace. Rows "regime": seconds a failed call takes | failure probability q | share of time Unknown | '
          'Unknown spells of 300 s or more per hour')
    for lat in (0.0, 2.0, 10.0):
        print('  attempts | %.0f | %d' % (lat, heartbeat_unknown(1.0, hours=1, fail_after=lat)['attempts_per_grace']))
    for lat in (0.0, 2.0, 10.0):
        for q in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
            r = heartbeat_unknown(q, hours=200, fail_after=lat)
            print('  regime | %.0f | %.2f | %.3f | %.3f' % (lat, q, r['unknown_share'], r['long_spells_per_hour']))
