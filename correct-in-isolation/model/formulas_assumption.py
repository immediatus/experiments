"""Closed forms of Part 4, a shared assumption: how often a start-time cycle binds, how long a webhook that
rejects its own pods lasts, and how long recovery waits on doubling retries.

Every input is a documented contract or a named parameter; defaults are the series' specimen."""
import math



def bind_probability(n, u, k):
    """Probability that k node failures, all sets equally likely among n nodes, take out every
    node of a start-time cycle whose replicas occupy u distinct nodes: C(n - u, k - u) / C(n, k),
    zero when k < u. Spreading replicas lowers it; at k = n it is one whatever the spread."""
    if k < u:
        return 0.0
    return math.comb(n - u, k - u) / math.comb(n, k)


def rejection_life(replicas, node_mtbf):
    """Expected time until a webhook that rejects its own pods has lost every replica, when each node
    holding a replica fails independently at rate 1 / node_mtbf and a lost replica is never replaced:
    the mean of the largest of `replicas` exponential times, node_mtbf times the harmonic number."""
    return node_mtbf * math.fsum(1.0 / i for i in range(1, replicas + 1))


def app_loss_distribution(app_replicas, webhook_replicas):
    """Replicas an application guarded by a webhook that rejects its own pods loses to one rolling drain
    under failurePolicy Fail, over drain orders all equally likely: the application loses exactly the
    replicas whose nodes come after the webhook's last, so with each on its own nodes it loses j with
    probability C(n_a + n_w - j - 1, n_w - 1) / C(n_a + n_w, n_w), and n_a / (n_w + 1) on average."""
    na, nw = app_replicas, webhook_replicas
    total = math.comb(na + nw, nw)
    return {j: math.comb(na + nw - j - 1, nw - 1) / total for j in range(na + 1)}


def workqueue_retry_after(outage, base=0.005, cap=1000.0):
    """The first retry at or after `outage` of a controller whose every sync fails until then, on
    client-go's default controller rate limiter: the k-th failure waits base * 2^(k-1), capped at
    `cap` (5 ms and 1000 s), so retries fall at base (2^k - 1) until the cap. Before the cap the retry
    comes before twice the outage plus base."""
    gaps = []
    while math.fsum(gaps) < outage:
        gaps.append(min(base * 2 ** len(gaps), cap))
    return math.fsum(gaps)


def kubelet_start_after(ready, first_start, run, base=10.0, cap=300.0):
    """The first start of a container, at or after `ready`, when every earlier start crashes after
    `run` seconds because a dependency is not up: the kubelet restarts it after 10, 20, 40 s and so on,
    capped at 300 s (Pod Lifecycle, container restart policy). A cap below the base, which
    KubeletCrashLoopBackOffMax allows down to 1 s, also sets the first delay (Pod Lifecycle: "the initial
    delay will instead be set to the configured maximum")."""
    base = min(base, cap)
    steps = [first_start]
    while math.fsum(steps) < ready:
        steps.append(run + min(base * 2 ** (len(steps) - 1), cap))
    return math.fsum(steps)


def cold_start_chain(dns_ready, webhook_first_start=30.0, crash_after=5.0, readiness=10.0, pod_start=90.0,
                     base=10.0, cap=300.0):
    """A full restart at t = 0 of three components in a chain: DNS ready at dns_ready; a webhook whose
    container crashes until DNS answers, first started at webhook_first_start, ready `readiness` after a
    start that finds DNS up; an application whose pods the webhook must admit (failurePolicy Fail), its
    ReplicaSet retrying from t = 0 on the workqueue's backoff, its pod ready pod_start after admission.
    Returns the ready times with the documented backoffs and with instant retries. base and cap are the
    kubelet's first restart delay and its ceiling: 10 s and 300 s by default, a per-node cap of 1 s to
    300 s under KubeletCrashLoopBackOffMax, 1 s and 60 s under ReduceDefaultCrashLoopBackOffDecay."""
    webhook = kubelet_start_after(dns_ready, webhook_first_start, crash_after, base, cap) + readiness
    webhook_ideal = max(dns_ready, webhook_first_start) + readiness
    app = workqueue_retry_after(webhook) + pod_start
    app_ideal = webhook_ideal + pod_start
    return {'webhook_ready': webhook, 'webhook_ready_ideal': webhook_ideal, 'app_ready': app, 'app_ready_ideal': app_ideal}


def cycle_mean_time_to_bind(replicas, node_mtbf, window):
    """Mean time until every replica of a webhook that must admit its own replacements is down at once,
    each replica's node failing at rate 1 / node_mtbf and its replica down for `window` after each
    failure (until it is evicted and restarted elsewhere): about 1 / (Z lam (lam w)^(Z - 1)) when
    lam w is small, exactly the mean time between failures for one replica."""
    lam = 1.0 / node_mtbf
    return 1.0 / (replicas * lam * (lam * window) ** (replicas - 1))


def stalled_rollout(replicas, max_unavailable=0.25, max_surge=0.25, rejects_own=True):
    """Where a rolling update of a webhook's own Deployment ends (Deployment docs: maxUnavailable rounded
    down, maxSurge rounded up, both 25% by default). The old ReplicaSet is scaled down by maxUnavailable at
    once, leaving the new one room for the surge plus that; a webhook whose running pods reject its own pods
    rejects every new pod, so the rollout stalls there and the old pods scaled down are not replaced, by
    either version. Without the rejection edge the rollout completes."""
    down = math.floor(max_unavailable * replicas)
    surge = math.ceil(max_surge * replicas)
    if not rejects_own:
        return {'old': 0, 'new': replicas, 'new_desired': replicas}
    return {'old': replicas - down, 'new': 0, 'new_desired': surge + down}
