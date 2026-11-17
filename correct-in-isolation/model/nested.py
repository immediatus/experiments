"""A pod autoscaler nested in a node autoscaler, each following its documented rule. Units:
seconds; capacity in pod requests.

Pod loop (Kubernetes HPA concept page): every sync period, ratio = average utilisation /
target, with pods not yet ready, pending ones included, counted at 0% on scale-up; desired =
ceil(ratio x replicas) when the ratio leaves 1 +- tol, capped by the default scale-up policy at
the larger of 100% of current replicas and 4 pods per sync of 15 s. A ready pod's utilisation
saturates at its limit.
Node loop (Cluster Autoscaler FAQ): every scan interval, if pods are unschedulable (pending
after the scheduler has placed what fits), add the nodes they need beyond the nodes already
being provisioned; a node is ready tau_node after it
is requested. Scheduler: a pending pod starts as soon as a slot is free and is ready tau_pod
later.
"""
import math


def simulate(k, n0=16, target=0.5, limit=1.0, per_node=8, headroom=0, tau_pod=90, tau_node=210,
             scan=10, sync=15, tol=0.1, oracle=False, dt=5, horizon=14400, metric='utilization',
             buffer_pct=0, shortfall=None):
    """Seconds from a k-fold step in demand until ready pods' limits cover it, or None within the
    horizon. headroom is free pod slots held in advance beyond the n0 running pods. With oracle,
    the node loop provisions for the final need at the first pending pod (the separated case).
    metric 'utilization' is the documented CPU rule, ready pods only and saturated at the limit;
    'load' is a per-pod average of load measured where requests arrive, which does not saturate and
    does not wait for pods to be ready: desired replicas are total load over the per-pod target.
    buffer_pct sizes a capacity buffer as a percentage of the current replica count (the Cluster
    Autoscaler's CapacityBuffer API, field `percentage`, rounded up): the node loop sees its unfilled
    part as pending pods, so it starts filled and is topped up at every scan as replicas grow, and
    real pods use its slots without preempting anything. A list passed as `shortfall` receives the pod-seconds
    of demand short of the ready pods' limits until capacity meets the surge."""
    demand = k * n0 * target
    need = math.ceil(demand / limit - 1e-9)
    nodes = math.ceil((n0 + max(headroom, math.ceil(buffer_pct * n0 / 100 - 1e-9))) / per_node)
    free = nodes * per_node - n0
    ready, starting, pending, provisioning = n0, [], 0, []
    total, done = n0, False
    t, lost = 0, []
    while t <= horizon:
        free += per_node * sum(1 for x in provisioning if x <= t)
        provisioning = [x for x in provisioning if x > t]
        placed = min(free, pending)
        free, pending = free - placed, pending - placed
        starting += [t + tau_pod] * placed
        ready += sum(1 for x in starting if x <= t)
        starting = [x for x in starting if x > t]
        if ready >= need:
            if shortfall is not None:
                shortfall.append(math.fsum(lost))
            return t
        lost.append(max(0.0, demand / limit - ready) * dt)
        if t % sync == 0:
            ratio = (demand / total / target) if metric == 'load' else (ready * min(demand / ready, limit) / total / target)
            if ratio > 1 + tol:
                desired = math.ceil(ratio * total - 1e-9)
                desired = min(desired, max(2 * total, total + 4))   # default scale-up policy: 100% or 4 pods per 15 s
                if desired > total:
                    pending, total = pending + desired - total, desired
                    placed = min(free, pending)          # the scheduler places new pods first;
                    free, pending = free - placed, pending - placed
                    starting += [t + tau_pod] * placed   # only the rest are unschedulable
        short = max(0, math.ceil(buffer_pct * total / 100 - 1e-9) - free) if buffer_pct else 0
        if t % scan == 0 and (pending > 0 or short > 0):
            if oracle:
                add = 0 if done else math.ceil(max(0, need - nodes * per_node) / per_node)
                done = True
            else:
                add = math.ceil(max(0, pending + short - len(provisioning) * per_node) / per_node)
            provisioning += [t + tau_node] * add
            nodes += add
        t += dt
    return None



def simulate_two_surges(gap, k=30, n0=16, target=0.5, limit=1.0, per_node=8, tau_pod=90, tau_node=210,
                        scan=10, sync=15, tol=0.1, first_len=3600, stabilization=300, unneeded=600,
                        delay_after_add=600, bulk=10, dt=5, trace=None):
    """Two k-fold surges, the second starting `gap` seconds after the first ends, with both
    controllers' documented scale-down rules. Returns (seconds from the second surge's start until
    ready pods' limits cover it, node-seconds held above the base node count during the gap).

    Pod loop (HPA concept page, default behavior): every sync records a recommendation (the current
    replica count when the ratio is inside tolerance); scale-up acts at once, capped as in
    simulate(); scale-down goes to the highest recommendation of the last `stabilization` seconds
    (300 s), with no rate limit (the default policy allows 100% per 15 s); pending pods go first,
    then starting ones, then ready ones. Node loop (Cluster Autoscaler FAQ): when no scale-up is
    needed, a node free of the deployment's pods is unneeded; after `unneeded` seconds (10 min) it
    is terminated, empty nodes in bulk of up to `bulk` (10) per scan, and none within
    `delay_after_add` (10 min) of a scale-up. Running pods are taken as packed onto as few nodes as
    possible, so free slots form whole empty nodes.
    """
    base = n0 * target
    t_start2 = first_len + gap
    base_nodes = math.ceil(n0 / per_node)
    nodes = base_nodes
    ready, starting, pending, provisioning = n0, [], 0, []
    total, recs, last_add, empty_since, held = n0, [], -10 ** 9, [], 0
    t = 0
    while t <= t_start2 + 14400:
        surging = t < first_len or t >= t_start2
        demand = base * k if surging else base
        need = math.ceil(demand / limit - 1e-9)
        nodes += sum(1 for x in provisioning if x <= t)
        provisioning = [x for x in provisioning if x > t]
        placed = min(nodes * per_node - ready - len(starting), pending)
        pending -= placed
        starting += [t + tau_pod] * placed
        ready += sum(1 for x in starting if x <= t)
        starting = [x for x in starting if x > t]
        if trace is not None:
            trace.append((t, nodes, ready, len(starting), pending, total))
        if t >= t_start2 and ready >= need:
            return t - t_start2, held
        if first_len <= t < t_start2:
            held += (nodes + len(provisioning) - base_nodes) * dt
        if t % sync == 0:
            ratio = ready * min(demand / ready, limit) / total / target
            raw = math.ceil(ratio * total - 1e-9) if abs(ratio - 1) > tol else total
            recs = [(a, b) for a, b in recs if a > t - stabilization] + [(t, raw)]
            if raw > total:
                desired = min(raw, max(2 * total, total + 4))
                pending, total = pending + desired - total, desired
                placed = min(nodes * per_node - ready - len(starting), pending)
                pending -= placed
                starting += [t + tau_pod] * placed
            elif max(b for _, b in recs) < total:
                drop = total - max(1, max(b for _, b in recs))
                total -= drop
                take = min(drop, pending)
                pending -= take
                drop -= take
                take = min(drop, len(starting))
                starting = starting[:len(starting) - take]
                drop -= take
                ready -= drop
        if t % scan == 0:
            unschedulable = pending - len(provisioning) * per_node
            if unschedulable > 0:
                provisioning += [t + tau_node] * math.ceil(unschedulable / per_node)
                last_add = t
            empty = (nodes * per_node - ready - len(starting)) // per_node
            empty_since = empty_since[:empty] + [t] * max(0, empty - len(empty_since))
            if pending == 0 and t - last_add >= delay_after_add:
                gone = sum(1 for s in empty_since if t - s >= unneeded)
                gone = min(gone, bulk, nodes - base_nodes)
                nodes -= gone
                empty_since = empty_since[gone:]
        t += dt
    return None, held
