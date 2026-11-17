"""Recovery of replicated components with start-time dependencies. A component is down when
every node holding one of its replicas has failed; a down component can start again once each
component it needs to start has at least one replica up. Recovery runs to its fixpoint.

Start-time edges in the Kubernetes instance come from documented contracts: a pod in a
namespace needs every admission webhook with failurePolicy Fail whose selectors match it
(Dynamic Admission Control), which is how a webhook that intercepts "resources required to
start its own Pods" deadlocks (Admission webhook good practices, "Avoid self-mutations").

rolling_drain() separates two kinds of edge. An availability edge holds when a webhook with
failurePolicy Fail must be up to admit a pod. A rejection edge holds when a running webhook's rules
reject the pod; an explicit rejection "always denies the API request, regardless of the
failurePolicy setting" (Dynamic Admission Control). A drain evicts through the Eviction API, which
refuses an eviction that would break a PodDisruptionBudget (API-initiated eviction).
"""
import itertools
import math
import random


def recover(placement, needs, failed):
    """Components still down once recovery stops.

    placement: component -> set of nodes holding its replicas.
    needs: component -> set of components it needs in order to start.
    failed: set of failed nodes, which come back empty.
    """
    down = {c for c, nodes in placement.items() if nodes <= failed}
    changed = True
    while changed:
        changed = False
        for c in sorted(down):
            if not (needs.get(c, set()) & down):
                down.discard(c)
                changed = True
    return down


def unrecoverable_fraction(placement, needs, nodes, k):
    """Share of the k-node failure sets, all equally likely, after which some component never
    comes back; exact, by enumeration."""
    bad = total = 0
    for failed in itertools.combinations(sorted(nodes), k):
        total += 1
        bad += bool(recover(placement, needs, set(failed)))
    return bad / total


def each_component_check(placement, needs, failed):
    """The per-component check, a component at a time: it guarantees to start whenever all it
    needs is up. True for every component on every trace, including one where nothing ever
    starts, because the guarantee is conditional on the others."""
    down = recover(placement, needs, failed)
    return all(bool(needs.get(c, set()) & down) or c not in down for c in placement)


def rolling_drain(placement, needs, rejects, order, min_available=None, bypass=False):
    """Drain the nodes one at a time in `order`, as a rolling node upgrade does, each node coming back
    empty before the next is drained.

    placement: component -> list of nodes holding its replicas, one per entry.
    needs: component -> webhooks with failurePolicy Fail that must be up to admit its pods.
    rejects: component -> webhooks whose rules reject its pods while they run.
    min_available: component -> minAvailable of its PodDisruptionBudget.
    Each evicted replica is replaced at once, on a node already drained, if its pod is admitted: every
    webhook it needs is up and no webhook that rejects it is up. An eviction that would leave fewer
    healthy replicas than the budget is refused, and the drain stalls there.
    Returns {'replicas': component -> replicas at the end, 'stalled': the node the drain stalled on, or None}.
    With bypass, an operator meets each refused eviction as the eviction guide suggests, by deleting the
    pod directly, which the budget does not govern; the result then also lists the nodes where that
    happened under 'bypassed'.
    """
    budget = min_available or {}
    count = {c: len(nodes) for c, nodes in placement.items()}
    def up(w):
        return count.get(w, 0) > 0
    bypassed = []
    for node in order:
        for c in sorted(placement):
            for _ in range(placement[c].count(node)):
                if c in budget and count[c] - 1 < budget[c]:
                    if not bypass:
                        return {'replicas': count, 'stalled': node}
                    bypassed.append(node)
                count[c] -= 1
                admitted = all(up(w) for w in needs.get(c, ())) and not any(up(w) for w in rejects.get(c, ()))
                if admitted:
                    count[c] += 1
    if bypass:
        return {'replicas': count, 'stalled': None, 'bypassed': bypassed}
    return {'replicas': count, 'stalled': None}


def drain_losses(replicas, min_available):
    """Replicas a component whose own pods are rejected loses before a budget of min_available stalls the
    drain: each eviction the budget allows is one replica that cannot be replaced, n - m in all."""
    return replicas - min_available


def simulated_life(replicas, node_mtbf, runs=20000, seed=1):
    """Mean, over `runs` seeded draws, of the time until every node holding one of `replicas` replicas
    has failed once, each failing at an exponential time with mean node_mtbf: the life of a webhook
    that rejects its own pods, which replaces no replica it loses."""
    rng = random.Random(seed)
    return math.fsum(max(rng.expovariate(1.0 / node_mtbf) for _ in range(replicas)) for _ in range(runs)) / runs


def drain_order_losses(placement, needs, rejects, orders=2000, seed=1, min_available=None):
    """Distribution of the application's replicas lost to one rolling drain, over `orders` seeded random
    drain orders of the nodes in placement: {replicas lost: number of orders}."""
    rng = random.Random(seed)
    nodes = sorted({n for v in placement.values() for n in v})
    start = len(placement['app'])
    dist = {}
    for _ in range(orders):
        order = nodes[:]
        rng.shuffle(order)
        lost = start - rolling_drain(placement, needs, rejects, order, min_available)['replicas']['app']
        dist[lost] = dist.get(lost, 0) + 1
    return dict(sorted(dist.items()))


def placed_drain(placement, needs, rejects, order, min_available=None, policy='spread', nodes=None):
    """rolling_drain with each replacement placed on a node, as the scheduler would place it, so that a
    replacement put on a node not yet drained is evicted again when that node's turn comes.

    policy: 'out of reach' puts every replacement where no later drain reaches it, which is
    rolling_drain; 'spread' puts it on the schedulable node with the fewest pods (the scheduler's
    default, LeastAllocated); 'pack' on the one with the most (MostAllocated). Ties go to the lowest
    node number. The node being drained is cordoned; every other node, drained or not, is
    schedulable. nodes is the number of nodes, numbered from 0.
    Returns {'replicas', 'stalled', 'evictions'}.
    """
    budget = min_available or {}
    nodes = nodes if nodes is not None else 1 + max(n for v in placement.values() for n in v)
    where = [(c, n) for c in sorted(placement) for n in placement[c]]
    count = {c: len(v) for c, v in placement.items()}
    def up(w):
        return count.get(w, 0) > 0
    evictions = 0
    for node in order:
        residents = sorted((i for i, (c, n) in enumerate(where) if n == node), key=lambda i: (where[i][0], i))
        for i in residents:
            c = where[i][0]
            if c in budget and count[c] - 1 < budget[c]:
                return {'replicas': count, 'stalled': node, 'evictions': evictions}
            count[c] -= 1
            evictions += 1
            where[i] = (c, None)
            admitted = all(up(w) for w in needs.get(c, ())) and not any(up(w) for w in rejects.get(c, ()))
            if not admitted:
                continue
            count[c] += 1
            if policy == 'out of reach':
                where[i] = (c, 'out')
                continue
            load = {m: 0 for m in range(nodes) if m != node}
            for _, m in where:
                if m in load:
                    load[m] += 1
            pick = min if policy == 'spread' else max
            target = pick(sorted(load), key=lambda m: load[m])
            where[i] = (c, target)
    return {'replicas': count, 'stalled': None, 'evictions': evictions}


def simulated_time_to_bind(replicas, node_mtbf, window, runs=2000, seed=1):
    """Mean, over seeded runs, of the time until a node failure finds every other replica already down:
    each replica runs for an exponential time with mean node_mtbf, is then down for `window`, and comes
    back on another node only if some replica is up to admit it, which holds until the moment of
    binding."""
    rng = random.Random(seed)
    times = []
    for _ in range(runs):
        down_until = [0.0] * replicas
        next_fail = [rng.expovariate(1.0 / node_mtbf) for _ in range(replicas)]
        while True:
            i = min(range(replicas), key=lambda k: next_fail[k])
            t = next_fail[i]
            if all(down_until[k] > t for k in range(replicas) if k != i):
                times.append(t)
                break
            down_until[i] = t + window
            next_fail[i] = t + window + rng.expovariate(1.0 / node_mtbf)
    return math.fsum(times) / runs


def heartbeat_unknown(q, hours=10, seed=1, renew=10.0, first=0.2, cap=7.0, grace=50.0, long_spell=300.0, fail_after=0.0):
    """One node's Lease renewals behind a webhook that fails each call with probability q: after a
    success the kubelet renews again `renew` seconds later; after a failure it retries after `first`
    seconds, doubling, capped at `cap` (Node Status, heartbeats). The node is Unknown whenever no renewal
    has succeeded for `grace` seconds. A failed call returns `fail_after` seconds after it starts, 0 for a
    refused connection and the webhook's timeout for one that hangs, and the backoff starts then. Returns
    the share of time Unknown, the rate of Unknown spells of at least `long_spell` seconds (after which
    tolerating pods are evicted), and the attempts a node gets after a success that start in time to
    renew before it turns Unknown."""
    rng = random.Random(seed)
    end = hours * 3600.0
    t, last_ok, backoff = 0.0, 0.0, first
    unknown, spells = [], 0
    t = renew
    while t < end:
        if rng.random() >= q:
            if t - last_ok > grace:
                spell = t - (last_ok + grace)
                unknown.append(spell)
                spells += spell >= long_spell
            last_ok, backoff = t, first
            t += renew
        else:
            t += fail_after + backoff
            backoff = min(backoff * 2, cap)
    if end - last_ok > grace:
        spell = end - (last_ok + grace)
        unknown.append(spell)
        spells += spell >= long_spell
    attempts, a, b = 0, renew, first
    while a <= grace:
        attempts += 1
        a += fail_after + b
        b = min(b * 2, cap)
    return {'unknown_share': math.fsum(unknown) / end, 'long_spells_per_hour': spells / hours, 'attempts_per_grace': attempts}


def eviction_regime(unhealthy_share, nodes, eligible_per_hour, rate=0.1, secondary=0.01, threshold=0.55, large=50):
    """Node evictions per hour under the node controller's documented limits (Nodes, rate limits on
    eviction), for one zone holding every node: none when every node is unhealthy, which it reads as a
    connectivity problem; at an unhealthy share of at least the threshold, stopped in a cluster of `large`
    nodes or fewer and `secondary` nodes per second above; otherwise `rate` nodes per second. The result is
    the smaller of that limit and the nodes eligible for eviction per hour."""
    if unhealthy_share >= 1.0:
        return 0.0
    if unhealthy_share >= threshold:
        limit = 0.0 if nodes <= large else secondary * 3600.0
    else:
        limit = rate * 3600.0
    return min(limit, eligible_per_hour)
