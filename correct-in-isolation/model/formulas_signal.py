"""Closed forms of Part 1, a shared signal: the gain matrices and relative gains of the paired autoscalers, the
rest band and the staircase, the history statistic, the split pairing through the heap, and the tail of usage.

Every input is a documented contract or a named parameter; defaults are the series' specimen."""
import math
from statistics import NormalDist


def relative_gain_array(g):
    """Bristol's relative gain array of a 2x2 steady-state gain matrix g = [[g11, g12], [g21, g22]],
    the elementwise product of g with the transpose of its inverse.

    Returns [[l, 1 - l], [1 - l, l]] with l = 1 / (1 - g12 g21 / (g11 g22)); rows and columns sum
    to one. Returns None when g is singular, where the array diverges and no pairing of inputs to
    outputs is defined.
    """
    (g11, g12), (g21, g22) = g
    det = g11 * g22 - g12 * g21
    if abs(det) < 1e-12 * max(1.0, abs(g11 * g22), abs(g12 * g21)):
        return None
    lam = g11 * g22 / det
    return [[lam, 1 - lam], [1 - lam, lam]]


def same_metric_gain():
    """Gain matrix, in log coordinates, of a horizontal loop (input log N, replicas) and a vertical
    loop (input log r, request per pod) that both hold utilisation u = D / (N r): both outputs are
    log u = log D - log N - log r, so the two rows are equal."""
    return [[-1.0, -1.0], [-1.0, -1.0]]


def split_metric_gain(beta=0.0, theta=1.0):
    """Gain matrix, in log coordinates, of a horizontal loop on CPU utilisation and a vertical loop
    on memory utilisation, the pairing the VPA documentation recommends.

    beta is the elasticity of per-pod CPU use with respect to the memory request (garbage
    collection rising as a heap sized from the memory limit shrinks); theta is the share of memory
    use that scales with per-pod load. Outputs are log CPU utilisation and log memory utilisation;
    inputs are log N and log memory request.
    """
    return [[-1.0, -beta], [-theta, -1.0]]


def vpa_utilisation(margin=0.15, q=1.0):
    """Utilisation at which the vertical loop holds a pod: the request is (1 + margin) times the
    usage percentile, and the percentile is q times mean usage, so u = 1 / ((1 + margin) q)."""
    return 1.0 / ((1.0 + margin) * q)


def equilibrium_band(margin=0.15, q=1.0, tol=0.1, vtol=0.0):
    """The horizontal targets u_h for which the two loops on one metric have an equilibrium.

    The horizontal loop takes no action while u / u_h lies within 1 +- tol. The vertical loop's
    target holds u at v = 1 / ((1 + margin) q); its updater leaves a pod's request alone while it
    lies within a relative distance vtol of the target (VPA documentation: updates when requests
    are outside the recommended bounds, or for pods older than 12 h when the recommendation
    differs by more than 10%), so u can rest anywhere in [v / (1 + vtol), v / (1 - vtol)].
    The loops rest where the two intervals overlap. Returns (lowest, highest) target.
    vtol = 0 is a steady load, whose percentile bounds close on the target; vtol = 0.1 is the
    widest the documented threshold allows for long-running pods."""
    v = vpa_utilisation(margin, q)
    return v / ((1.0 + tol) * (1.0 + vtol)), v / ((1.0 - tol) * (1.0 - vtol))


def directional_band(margin=0.15, q=1.0, tol_up=0.1, tol_down=0.1, vtol=0.0):
    """equilibrium_band with a tolerance per direction (HPAConfigurableTolerance, GA in Kubernetes
    1.37): the horizontal loop scales up only when u / u_h exceeds 1 + tol_up and down only when it
    falls below 1 - tol_down, so it rests anywhere in [u_h (1 - tol_down), u_h (1 + tol_up)]. The
    scale-up tolerance sets the band's low edge and the scale-down tolerance its high edge."""
    v = vpa_utilisation(margin, q)
    return v / ((1.0 + tol_up) * (1.0 + vtol)), v / ((1.0 - tol_down) * (1.0 - vtol))


def stopping_scale_up_tolerance(u_h, margin=0.15, q=1.0):
    """The smallest scale-up tolerance at which a target u_h rests on a steady load: the step factor
    minus one, 1 / ((1 + margin) q u_h) - 1, and 0 when u_h already lies at or above the band's low
    edge. 0.739 at a 50% target and the documented margin."""
    return max(0.0, 1.0 / ((1.0 + margin) * q * u_h) - 1.0)


def step_interval(half_life=24.0, percentile=0.9):
    """Hours between the vertical loop's moves while the pairing drifts on a steady load. Per-pod
    usage is constant between moves and higher before them, so the p-th percentile of a history
    whose samples lose half their weight every half_life stays on the previous level until the
    current level carries a fraction p of the weight: half_life x log2(1 / (1 - p)). 79.7 hours at
    the documented defaults."""
    return half_life * math.log2(1.0 / (1.0 - percentile))


def step_factor(u_h, margin=0.15, bucket=1.0):
    """The factor by which one move multiplies the replica count: the request falls to (1 + margin)
    times the current per-pod usage, which the horizontal loop holds at u_h times the request, so
    replicas grow by 1 / ((1 + margin) u_h). A histogram that reports a bucket's upper edge, buckets
    `bucket` wide, makes the request up to that much larger and the factor that much smaller."""
    return 1.0 / ((1.0 + margin) * u_h * bucket)


def doubling_bracket(u_h, margin=0.15, half_life=24.0, percentile=0.9, tol=0.1, bucket=1.05):
    """(fastest, slowest) long-run replica doubling time on a steady load, in hours: one move every
    step_interval, each multiplying replicas by step_factor between its bucket-free value and its
    value at a full bucket. None when the factor does not exceed 1 + tol, where the horizontal loop
    takes no action after a move and the replica count does not grow: the target is then inside or
    above the band of Proposition 3."""
    if step_factor(u_h, margin) <= 1.0 + tol:
        return None
    s = step_interval(half_life, percentile) * math.log(2)
    lo = s / math.log(step_factor(u_h, margin))
    f = step_factor(u_h, margin, bucket)
    return lo, (s / math.log(f) if f > 1.0 + tol else float('inf'))


def prior_weight(prior, half_life=24.0):
    """Weight of a remembered history in units of one sample at the start: the seed sample at the starting
    usage, weight 1, plus each (factor, hours before the start, samples) burst at 2^(-hours / half_life) a
    sample, as hpa_vpa.simulate's prior lays it down. In the staircase all of it lies above the usage the
    horizontal loop holds, so it is both A0 and H0 of first_step_delay."""
    return 1.0 + math.fsum(count * 2.0 ** (-hours / half_life) for _, hours, count in prior)


def first_step_delay(above, total, rate=60.0, half_life=24.0, percentile=0.9):
    """Hours until the vertical recommender's percentile lets go of a remembered level: the history
    statistic of Part 1's seam. `above` is the remembered weight above the current usage and `total` the
    whole weight, both in units of one sample at the start; new samples arrive at `rate` an hour at the
    current usage, each weighted 2^(t / half_life). The percentile moves down once above <= (1 - p) of the
    total, which gives s1 = h log2(1 + ln2 (above / (1 - p) - total) / (rate h)); a long steady history
    (total = rate h / ln2, all of it above) gives step_interval's h log2(1 / (1 - p))."""
    need = above / (1.0 - percentile) - total
    if need <= 0:
        return 0.0
    return half_life * math.log2(1.0 + math.log(2) * need / (rate * half_life))


def matched_tolerance(u_h, margin=0.15, q=1.0):
    """The per-direction scale-up tolerance at which a pair on a shared CPU metric rests at target u_h:
    the vertical loop holds utilization v = 1/((1+m)q), and v sits at the horizontal loop's scale-up edge
    when u_h (1 + tol_up) = v, so tol_up = v / u_h - 1. Meaningful for u_h <= v."""
    return vpa_utilisation(margin, q) / u_h - 1.0


def resting_rounds(k, u_h, margin=0.15, q=1.0, limit_ratio=1.0, policy=2.0):
    """Rounds of a saturated metric for a surge to k times the demand a pair resting at target u_h with the
    matched scale-up tolerance carries (Proposition 40). The pods run at v = 1/((1+m)q) of their request,
    the need is k v times the running pods at the limit. A round's first action grows the replicas by the
    growth factor g = limit_ratio / u_h, at most `policy` (the default scale-up policy doubles per sync).
    After it the ratio, which counts not-yet-ready pods at zero, is at most g / policy, below the matched
    gate 1 + tol_up = v / u_h whenever v >= 1 / policy, so no second action comes in that round: the growth
    per round is min(g, policy), and the rounds are ceil(ln(k v / limit_ratio) / ln(min(g, policy)))."""
    v = vpa_utilisation(margin, q)
    g = min(limit_ratio / u_h, policy)
    return math.ceil(math.log(k * v / limit_ratio) / math.log(g) - 1e-9)


def coupled_relative_gain(beta, theta):
    """The (1, 1) relative gain of the recommended split pairing with memory-to-CPU coupling,
    1 / (1 - beta theta); None at beta theta = 1, where the pairing has no defined gain."""
    rga = relative_gain_array(split_metric_gain(beta, theta))
    return None if rga is None else rga[0][0]


def split_gain_matrix(beta, theta, theta_live=0.0, xi=0.0):
    """The split pairing's gain matrix with the heap's structure explicit: actuators log N and log r_mem,
    outputs log CPU and log memory utilization. Collection CPU has elasticity -beta in the heap over the live
    set it traces; the live set follows per-pod load with share theta_live, so scaling out also raises that
    ratio; observed memory follows load with share theta and the request with elasticity xi."""
    return [[-(1.0 + beta * theta_live), -beta], [-theta, -(1.0 - xi)]]


def split_relative_gain(beta, theta, theta_live=0.0, xi=0.0):
    """The horizontal loop's relative gain in the split pairing,
    (1 + beta theta_live)(1 - xi) / ((1 + beta theta_live)(1 - xi) - beta theta); None where singular.
    With theta_live = xi = 0 it is 1 / (1 - beta theta)."""
    a = (1.0 + beta * theta_live) * (1.0 - xi)
    d = a - beta * theta
    return None if abs(d) < 1e-12 else a / d


def singular_heap_share(beta):
    """The heap's share of observed memory below which the split pairing turns singular when the live set does
    not follow load. Only memory outside the heap then follows load, so theta is at most 1 - s_H, and the gain
    1 / (1 - beta theta) turns singular where beta (1 - s_H) = 1, at s_H = 1 - 1 / beta. None when beta is at
    most one: the gain then stays finite at every heap share."""
    if beta <= 1.0:
        return None
    return 1.0 - 1.0 / beta


def off_heap_gain(beta, heap_share):
    """The split pairing's relative gain with a live set that does not follow load and all load-following
    memory outside a heap that holds heap_share of observed memory: theta = 1 - heap_share. None where
    singular."""
    return split_relative_gain(beta, 1.0 - heap_share)


def critical_xi(beta, theta, theta_live=0.0):
    """The elasticity of observed memory with respect to the request at which the split pairing turns
    singular: 1 - beta theta / (1 + beta theta_live)."""
    return 1.0 - beta * theta / (1.0 + beta * theta_live)


def elasticity(x1, y1, x2, y2):
    """Elasticity of y with respect to x between two measured points, ln(y1 / y2) / ln(x2 / x1),
    taken positive when y falls as x rises."""
    return math.log(y1 / y2) / math.log(x2 / x1)


def custom_metric_gain(gamma, epsilon=1.0):
    """Gain matrix, in log coordinates, of a horizontal loop on a custom metric and a vertical
    loop on CPU utilization. The metric is a function of load per pod over a pod's service rate,
    with elasticity epsilon, and the service rate scales with the CPU request with elasticity
    gamma (through the limit the vertical autoscaler keeps proportional to the request, which the
    kernel enforces by throttling). Inputs log N and log r; outputs the log metric and log u."""
    return [[-epsilon, -epsilon * gamma], [-1.0, -1.0]]


def custom_metric_relative_gain(gamma, epsilon=1.0):
    """The horizontal loop's relative gain with a custom metric, 1 / (1 - gamma), whatever the
    metric's own elasticity epsilon; None at gamma = 1, where the custom metric carries the same
    signal as CPU utilization."""
    rga = relative_gain_array(custom_metric_gain(gamma, epsilon))
    return None if rga is None else rga[0][0]


def resting_margin(u_h, q=1.0, tol=0.1, vtol=0.0):
    """The vertical margin fractions at which a shared-metric pairing with horizontal target u_h
    can rest: (lowest, highest), from equilibrium_band. The request is then (1 + m) q times mean
    usage per pod, between 1 / (u_h (1 + tol)(1 + vtol)) and 1 / (u_h (1 - tol)(1 - vtol)),
    whatever q: resting requires the vertical loop to size requests from the horizontal target."""
    return (1.0 / (u_h * q * (1.0 + tol) * (1.0 + vtol)) - 1.0,
            1.0 / (u_h * q * (1.0 - tol) * (1.0 - vtol)) - 1.0)


def _z(p):
    return NormalDist().inv_cdf(p)


def lognormal_q(sigma, p=0.9):
    """Percentile-to-mean ratio of per-pod usage when each sample is the mean times a lognormal factor
    of mean one and shape sigma: the factor is exp(sigma Z - sigma^2 / 2), so its p-quantile is
    exp(z_p sigma - sigma^2 / 2). It rises from 1, peaks at sigma = z_p with exp(z_p^2 / 2), 2.27 for
    the 90th percentile, and falls toward zero for heavier tails."""
    return math.exp(_z(p) * sigma - sigma * sigma / 2.0)


def pareto_q(alpha, p=0.9):
    """The same ratio for a Pareto factor with tail index alpha > 1, scaled to mean one: the
    p-quantile over the mean, (1 - p)^(-1 / alpha) (alpha - 1) / alpha."""
    return (1.0 - p) ** (-1.0 / alpha) * (alpha - 1.0) / alpha


def regime(u_h, q, margin=0.15, tol=0.1, vtol=0.0):
    """Which way the paired loops move on a steady mean load: 'drift up' (replicas climb) when the
    target lies below the rest band of equilibrium_band, 'drift down' when above it, 'rest' inside."""
    low, high = equilibrium_band(margin, q, tol, vtol)
    if u_h < low:
        return 'drift up'
    if u_h > high:
        return 'drift down'
    return 'rest'


def regime_boundaries(u_h, margin=0.15, tol=0.1, p=0.9):
    """The lognormal shapes sigma at which the regime of a target u_h changes: the roots of
    lognormal_q(sigma) = q_edge for the two band edges q_low = 1 / ((1 + margin) u_h (1 + tol)) and
    q_high = 1 / ((1 + margin) u_h (1 - tol)), sigma = z_p -+ sqrt(z_p^2 - 2 ln q_edge). Sorted."""
    z = _z(p)
    out = []
    for q in (1.0 / ((1 + margin) * u_h * (1 + tol)), 1.0 / ((1 + margin) * u_h * (1 - tol))):
        d = z * z - 2.0 * math.log(q)
        if d >= 0:
            out += [z - math.sqrt(d), z + math.sqrt(d)]
    return sorted(out)


def pod_mean_cv(sigma, n):
    """Coefficient of variation of the horizontal loop's reading, the mean of n pods' samples, each the mean
    times an independent lognormal factor of mean one and shape sigma: sqrt((exp(sigma^2) - 1) / n). The tail
    regimes assume it small, the limit of many pods."""
    return math.sqrt((math.exp(sigma * sigma) - 1.0) / n)


def spike_share(sigma, c):
    """Share of the mean usage carried by samples above c times the mean, for a lognormal factor of mean one
    and shape sigma: the size-biased tail, 1 - Phi((ln c - sigma^2 / 2) / sigma). A node with c times a pod's
    mean usage in cores cannot serve that share, so the regimes that need it are those of unclipped samples."""
    if sigma == 0:
        return 0.0
    x = (math.log(c) - sigma * sigma / 2.0) / sigma
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def drift_rate(u_h, margin=0.15, tol=0.1, half_life=24.0, percentile=0.9):
    """Long-run growth rate of the replica count on a steady load, per hour, from the closed form of
    Proposition 4 without bucket rounding: ln F / s* while the step factor F = 1 / ((1 + margin) u_h)
    exceeds 1 + tol, and zero once it does not. At the band's low edge F = 1 + tol, so the rate jumps from
    ln(1 + tol) / s* to zero: a first-order transition in the target."""
    f = step_factor(u_h, margin)
    return math.log(f) / step_interval(half_life, percentile) if f > 1.0 + tol else 0.0


def max_resting_target(q, tol=0.1):
    """The highest horizontal target at which the paired loops can rest with some vertical margin of at
    least zero: the band of equilibrium_band reaches u_h only if u_h <= 1 / ((1 + m) q (1 - tol)), largest
    at m = 0. Targets above it drift down whatever the margin."""
    return 1.0 / (q * (1.0 - tol))
