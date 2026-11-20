"""Closed forms of Part 2, a shared time scale: rounds of a nested surge, headroom and its price, the memory of the
two scale-down windows, the cost of holding or releasing between surges, and the tail of surge sizes.

Every input is a documented contract or a named parameter; defaults are the series' specimen."""
import math


def rounds(k, target=0.5, limit=1.0):
    """Rounds a saturated utilisation metric needs before a k-fold overload is served, restated
    from "One Bit per Dead Time" (Proposition 2): ceil(log_g(k u* / l)), with growth factor
    g = l / u* per round, target u* as a fraction and limit l as a multiple of the request."""
    g = limit / target
    return max(0, math.ceil(math.log(k * target / limit) / math.log(g) - 1e-9))


def covered_rounds(headroom, n0, k, target=0.5, limit=1.0):
    """Rounds whose new pods all fit in the free pod slots held in advance: round j brings the
    replica count to min(n0 g^j, pods needed), so the first m rounds need n0 (g^m - 1) slots,
    capped at the pods the overload needs."""
    g = limit / target
    need = math.ceil(k * n0 * target / limit - 1e-9)
    m = 0
    while m < rounds(k, target, limit) and min(n0 * g ** (m + 1), need) - n0 <= headroom:
        m += 1
    return m


def headroom_for(m, n0, k=None, target=0.5, limit=1.0):
    """Free pod slots that cover the first m rounds, n0 (g^m - 1): each further round multiplies
    the price by about g and saves one node wait. Given the overload k, the last round is capped
    at the pods the overload needs, so the price never exceeds need - n0."""
    g = limit / target
    slots = n0 * (g ** m - 1)
    if k is not None:
        slots = min(slots, math.ceil(k * n0 * target / limit - 1e-9) - n0)
    return slots


def step_slots(c, n0, k, target=0.5, limit=1.0):
    """The fewest free pod slots that remove c node waits from a k-fold surge with no slot free otherwise: the
    pod loop sizes each round from its ready pods, so once n0 + H pods are ready the rounds continue from them,
    and the surge needs R - c further rounds once n0 + H reaches the need over g^(R - c):
    ceil(need g^(c - R)) - n0. Never more than headroom_for(c), which keeps the first c rounds free of pending
    pods, and equal to it when the need is n0 times a power of g."""
    r = rounds(k, target, limit)
    if not 1 <= c <= r:
        raise ValueError('c must lie between 1 and the %d rounds the surge needs' % r)
    g = limit / target
    need = math.ceil(k * n0 * target / limit - 1e-9)
    return math.ceil(need * g ** (c - r) - 1e-9) - n0


def nested_time(k, tau_pod, tau_node, m=0, target=0.5, limit=1.0):
    """Time to capacity, scan and sync latencies left out, when the node loop sees only the pods
    already pending: every round beyond the m covered by headroom waits for nodes,
    R tau_pod + (R - m) tau_node."""
    r = rounds(k, target, limit)
    return r * tau_pod + max(0, r - m) * tau_node


def separated_time(k, tau_pod, tau_node, m=0, target=0.5, limit=1.0):
    """Time to capacity, latencies left out, if the node loop provisioned for the final need at
    the first pending pod: one node wait at most, R tau_pod + tau_node when any round needs
    nodes."""
    r = rounds(k, target, limit)
    return r * tau_pod + (tau_node if r > m else 0)


def kept_rounds(gap, k, tau_pod, stabilization=300, unneeded=600, target=0.5, limit=1.0):
    """Rounds of a second k-fold surge that find the first surge's nodes still there. The pod loop
    removes the first surge's pods `stabilization` seconds after it ends; the node loop deletes the
    emptied nodes `unneeded` seconds later. Round r places its pods about gap + (r - 1) tau_pod
    after the first surge ends, so it keeps its nodes iff that is before stabilization + unneeded.
    Deletion is taken as instant: the documented bulk spreads it over a few scan intervals."""
    r = rounds(k, target, limit)
    return sum(1 for j in range(r) if gap + j * tau_pod < stabilization + unneeded)


def second_surge_time(gap, k, tau_pod, tau_node, stabilization=300, unneeded=600, target=0.5, limit=1.0):
    """Time to capacity for the second of two k-fold surges `gap` seconds apart, latencies left
    out: zero while the stabilization window still holds the pods, otherwise the nested time with
    the kept rounds as headroom, R tau_pod + (R - m) tau_node."""
    if gap < stabilization:
        return 0
    m = kept_rounds(gap, k, tau_pod, stabilization, unneeded, target, limit)
    return nested_time(k, tau_pod, tau_node, m, target, limit)


def expected_held(unneeded, mean_gap, spare, stabilization=300):
    """Node-seconds held above the base count between two surges, for gaps exponential with mean
    mean_gap: the spare nodes stay until the next surge or until stabilization + unneeded,
    spare * E[min(G, S + U)] = spare * mean_gap * (1 - exp(-(S + U) / mean_gap))."""
    return spare * mean_gap * (1 - math.exp(-(stabilization + unneeded) / mean_gap))


def expected_time(unneeded, mean_gap, k, tau_pod, tau_node, stabilization=300, target=0.5, limit=1.0):
    """Mean of second_surge_time over exponential gaps: R tau_pod once the gap passes S, and one
    node wait for each round j whose pods land after deletion, G >= max(S, S + U - j tau_pod)."""
    r = rounds(k, target, limit)
    d = stabilization + unneeded
    return (math.exp(-stabilization / mean_gap) * r * tau_pod
            + tau_node * math.fsum(math.exp(-max(stabilization, d - j * tau_pod) / mean_gap) for j in range(r)))


def gap_cost(unneeded, mean_gap, rate, k, tau_pod, tau_node, spare, stabilization=300):
    """Expected node-seconds held plus rate (node-seconds per second short of capacity) times the
    expected second-surge time: the scalar a supporting line of the second-surge region minimizes."""
    return (expected_held(unneeded, mean_gap, spare, stabilization)
            + rate * expected_time(unneeded, mean_gap, k, tau_pod, tau_node, stabilization))


def hold_through(mean_gap, rate, k, tau_node, spare, target=0.5, limit=1.0):
    """With memoryless gaps, holding until the next surge beats releasing at once iff the spare
    nodes held through a mean gap cost less than every round's node wait: spare mu < rate R tau_node."""
    return spare * mean_gap < rate * rounds(k, target, limit) * tau_node


def break_even(rate, k, tau_node, spare, target=0.5, limit=1.0):
    """The unneeded time whose holding cost equals the node waits it can save: rate R tau_node / spare."""
    return rate * rounds(k, target, limit) * tau_node / spare


def hindsight_cost(gap, rate, k, tau_pod, tau_node, spare, stabilization=300):
    """Least cost with the gap known (Corollary 1): release at once or hold through the gap and ramp."""
    r = rounds(k)
    return min(spare * min(gap, stabilization) + rate * second_surge_time(gap, k, tau_pod, tau_node, stabilization, 0),
               spare * gap + rate * second_surge_time(gap, k, tau_pod, tau_node, stabilization, gap + r * tau_pod))


def worst_ratio(unneeded, rate, k, tau_pod, tau_node, spare, stabilization=300):
    """Largest ratio, over gaps, of an unneeded time's cost to the hindsight cost. For gaps at or past
    S + U the cost is fixed and the hindsight cost does not fall, so gaps up to S + U suffice."""
    d = stabilization + unneeded
    worst = 1.0
    for g in [stabilization + i for i in range(int(unneeded) + 1)] + [d]:
        cost = spare * min(g, d) + rate * second_surge_time(g, k, tau_pod, tau_node, stabilization, unneeded)
        worst = max(worst, cost / hindsight_cost(g, rate, k, tau_pod, tau_node, spare, stabilization))
    return worst


def pod_break_even(rate, k, tau_pod, tau_node, spare, target=0.5, limit=1.0):
    """The pod loop's stabilization window whose holding cost equals the time it can save when the
    whole memory is kept as pods: a gap inside it is served at once, a gap past it pays the cold
    nested time, so the break-even is rate R (tau_pod + tau_node) / spare."""
    return rate * nested_time(k, tau_pod, tau_node, 0, target, limit) / spare


def pod_worst_ratio(window, rate, k, tau_pod, tau_node, spare):
    """Largest ratio, over gaps, of holding pods for `window` seconds (unneeded time 0) to the
    hindsight cost, the better of releasing at once (rate times the cold time) and holding the pods
    through the gap (spare times the gap). Gaps past the window add nothing to the ratio."""
    cold = rate * nested_time(k, tau_pod, tau_node)
    worst = 1.0
    for g in [i for i in range(1, int(window) + 1)] + [window]:
        cost = spare * min(g, window) + (cold if g >= window else 0)
        worst = max(worst, cost / min(spare * g, cold))
    return worst


WINDOW_CAP = 3600   # autoscaling/v2: stabilizationWindowSeconds "less than or equal to 3600 (one hour)"


def memory_split(memory):
    """Keep a post-surge memory of `memory` seconds as pods first, up to the stabilization window's
    documented cap, and the rest as nodes: (stabilization, unneeded)."""
    s = min(memory, WINDOW_CAP)
    return s, memory - s


def memory_cost(memory, mean_gap, rate, k, tau_pod, tau_node, spare):
    """Expected cost, node-seconds plus rate times seconds to capacity, of a memory kept as
    memory_split puts it, for exponential gaps."""
    s, u = memory_split(memory)
    return expected_held(u, mean_gap, spare, s) + rate * expected_time(u, mean_gap, k, tau_pod, tau_node, s)


def weibull_scale(mean_gap, shape):
    """Scale of a Weibull gap with the given mean: mean / Gamma(1 + 1/shape). Shape below 1 gives a
    falling hazard (surges cluster), 1 the exponential, above 1 a rising one (surges near-periodic)."""
    return mean_gap / math.gamma(1 + 1 / shape)


def weibull_pod_cost(window, shape, mean_gap, rate, k, tau_pod, tau_node, spare, steps=4000):
    """Expected cost of a memory kept as pods for `window` seconds (unneeded time 0) with Weibull
    gaps: spare * E[min(G, window)] + rate * C * P(G >= window), C the cold nested time. The first
    term is spare times the integral of the survival function, by the midpoint rule."""
    eta = weibull_scale(mean_gap, shape)
    def survival(t):
        return math.exp(-(t / eta) ** shape)
    h = window / steps
    held = math.fsum(survival((i + 0.5) * h) for i in range(steps)) * h
    return spare * held + rate * nested_time(k, tau_pod, tau_node) * survival(window)


def hazard_window(shape, mean_gap, rate, k, tau_pod, tau_node, spare):
    """The hazard rule for Weibull gaps: with a falling hazard (shape < 1) the cheapest window is
    where the hazard (shape / eta) (t / eta)^(shape - 1) falls to spare / (rate C), capped at the
    documented hour; with a hazard that does not fall there is no interior window (None)."""
    if shape >= 1:
        return None
    eta = weibull_scale(mean_gap, shape)
    threshold = spare / (rate * nested_time(k, tau_pod, tau_node))
    return min(eta * (threshold * eta / shape) ** (1 / (shape - 1)), WINDOW_CAP)


def _weibull(shape, mean_gap):
    eta = weibull_scale(mean_gap, shape)
    def survival(t):
        return math.exp(-(t / eta) ** shape) if t > 0 else 1.0
    def density(t):
        return (shape / eta) * (t / eta) ** (shape - 1) * survival(t) if t > 0 else 0.0
    return survival, density


def node_tail_cost(unneeded, shape, mean_gap, rate, k, tau_pod, tau_node, spare, stabilization=WINDOW_CAP, steps=20000):
    """Expected cost of a memory kept as pods for the capped window and then as nodes for `unneeded`
    seconds, Weibull gaps: spare * E[min(G, D)] + rate * E[T2], D = S + U, with E[T2] from
    Proposition 10: R tau_pod once the gap passes S, plus a node wait for each round j placed after
    deletion, G >= max(S, D - j tau_pod)."""
    survival, _ = _weibull(shape, mean_gap)
    d = stabilization + unneeded
    h = d / steps
    held = math.fsum(survival((i + 0.5) * h) for i in range(steps)) * h
    r = rounds(k)
    t2 = survival(stabilization) * r * tau_pod + tau_node * math.fsum(survival(max(stabilization, d - j * tau_pod)) for j in range(r))
    return spare * held + rate * t2


def node_tail_slope(unneeded, shape, mean_gap, rate, k, tau_pod, tau_node, spare, stabilization=WINDOW_CAP):
    """The lagged rule: d E[cost] / dU = spare * survival(D) - rate * tau_node * sum of the density at
    D - j tau_pod over the rounds whose placement time is still past the window, D - j tau_pod > S."""
    survival, density = _weibull(shape, mean_gap)
    d = stabilization + unneeded
    return spare * survival(d) - rate * tau_node * math.fsum(density(d - j * tau_pod) for j in range(rounds(k))
                                                       if d - j * tau_pod > stabilization)


def ramp_shortfall(k, n0, tau_pod, tau_node, c=0, target=0.5, limit=1.0, separated=False, slots=None):
    """Pod-seconds of demand short of capacity while a k-fold surge is met, on Proposition 9's ladder:
    the need N* = k n0 u / l taken as continuous, round j served by the n0 g^(j-1) pods ready before it
    and lasting tau_pod, plus tau_node when the round is past the c covered ones. Separated, only the
    first round waits for nodes. Scan and sync latencies and the partial-round penalty are left out. With
    `slots` free slots instead of c rounds, round j is covered when the pods it adds fit in them,
    min(n0 g^j, N*) - n0 <= slots, which covers the last round of a small surge with less than a round's price."""
    g = limit / target
    need = k * n0 * target / limit
    r = max(0, math.ceil(math.log(need / n0) / math.log(g) - 1e-9))
    total = []
    for j in range(1, r + 1):
        if separated:
            wait = j == 1
        elif slots is not None:
            wait = min(n0 * g ** j, need) - n0 > slots
        else:
            wait = j > c
        total.append((need - n0 * g ** (j - 1)) * (tau_pod + (tau_node if wait else 0)))
    return math.fsum(total)


def pareto_rounds_tail(j, alpha, g=2.0):
    """P(R >= j) for a need Pareto with exponent alpha above n0: the need passes n0 g^(j-1), which
    happens with probability g^(-alpha (j-1)), a geometric tail."""
    return 1.0 if j <= 1 else g ** (-alpha * (j - 1))


def pareto_mean_time(alpha, tau_pod, tau_node, g=2.0):
    """Mean nested time to capacity, (tau_pod + tau_node) E[R] = (tau_pod + tau_node) / (1 - g^-alpha):
    finite for every alpha > 0."""
    return (tau_pod + tau_node) / (1.0 - g ** (-alpha))


def pareto_shortfall(alpha, n0, tau_pod, tau_node, c=0, g=2.0, separated=False):
    """Mean of ramp_shortfall for a need Pareto with exponent alpha above n0. Each round j contributes
    E[(N* - n0 g^(j-1))^+] = n0 g^((j-1)(1-alpha)) / (alpha - 1) times its length, so the sum is
    n0 [tau_pod + tau_node g^(-c (alpha - 1))] / ((alpha - 1)(1 - g^(1 - alpha))) nested, and
    n0 tau_pod / ((alpha - 1)(1 - g^(1 - alpha))) + n0 tau_node / (alpha - 1) separated. Infinite for
    alpha <= 1."""
    if alpha <= 1.0:
        return math.inf
    base = n0 / ((alpha - 1.0) * (1.0 - g ** (1.0 - alpha)))
    if separated:
        return base * tau_pod + tau_node * n0 / (alpha - 1.0)
    return base * (tau_pod + tau_node * g ** (-c * (alpha - 1.0)))


def pareto_shortfall_slots(alpha, n0, tau_pod, tau_node, slots, g=2.0):
    """Mean of ramp_shortfall with `slots` free slots, need Pareto with exponent alpha above n0. Round j, served
    by x_j = n0 g^(j-1) ready pods, waits for nodes when n0 (g^j - 1) > slots and N* > y = n0 + slots, so its
    node-wait term is E[(N* - x_j)^+ ; N* > y]: n0^a x_j^(1-a) / (a - 1) once x_j >= y, and
    n0^a y^(1-a) / (a - 1) + (y - x_j) (n0 / y)^a before. Continuous in slots; infinite for alpha <= 1."""
    if alpha <= 1.0:
        return math.inf
    a = alpha
    y = n0 + slots
    pod = n0 / ((a - 1.0) * (1.0 - g ** (1.0 - a)))
    node, j = [], 1
    while True:
        x = n0 * g ** (j - 1)
        if x >= y:
            node.append(n0 * g ** ((j - 1) * (1.0 - a)) / ((a - 1.0) * (1.0 - g ** (1.0 - a))))
            break
        if n0 * (g ** j - 1.0) > slots:
            node.append(n0 ** a * y ** (1.0 - a) / (a - 1.0) + (y - x) * (n0 / y) ** a)
        j += 1
    return tau_pod * pod + tau_node * math.fsum(node)


def nesting_multiplier(alpha, g=2.0):
    """How many times the node-wait part of the mean shortfall nested exceeds it separated:
    1 / (1 - g^(1 - alpha)), which grows without bound as alpha falls to 1."""
    return math.inf if alpha <= 1.0 else 1.0 / (1.0 - g ** (1.0 - alpha))


def cover_cost(c, alpha, n0, price, mean_gap, tau_pod, tau_node, g=2.0):
    """Cost per surge of holding the slots that cover c rounds, n0 (g^c - 1), for a mean gap between
    surges, plus `price` slot-seconds for every pod-second short in the mean ramp."""
    return mean_gap * n0 * (g ** c - 1.0) + price * pareto_shortfall(alpha, n0, tau_pod, tau_node, c, g)


def optimal_cover(alpha, price, mean_gap, tau_node, g=2.0):
    """(x*, c*): the continuous optimum of cover_cost in x = g^c, x*^alpha = price tau_node /
    (mean_gap (1 - g^(1 - alpha))), and the best whole number of covered rounds next to it.
    The cover cannot go below none, so x* is held at one or more. No finite cover for alpha <= 1."""
    if alpha <= 1.0:
        return math.inf, None
    x = max(1.0, (price * tau_node / (mean_gap * (1.0 - g ** (1.0 - alpha)))) ** (1.0 / alpha))
    lo = max(0, math.floor(math.log(x) / math.log(g))) if x > 1.0 else 0
    best = min((lo, lo + 1), key=lambda c: cover_cost(c, alpha, 1.0, price, mean_gap, 0.0, tau_node, g))
    return x, best


def pareto_mle(sample, kmin, cap=None):
    """Maximum-likelihood tail exponent for sizes Pareto above kmin: count over the sum of ln(k / kmin).
    With readings capped at `cap`, as a replica count capped by maxReplicas is, the capped readings
    still add ln(cap / kmin) to the sum but are not counted, the estimate for right-censored data."""
    if cap is None:
        return len(sample) / math.fsum(math.log(k / kmin) for k in sample)
    return (sum(1 for k in sample if k < cap) /
            math.fsum(math.log(min(k, cap) / kmin) for k in sample))


def censored_naive(alpha, kmin, cap):
    """What pareto_mle without `cap` converges to on readings capped at `cap`: E[ln(min(K, cap) / kmin)]
    is (1 - (kmin / cap)^alpha) / alpha, so the estimate is alpha / (1 - (kmin / cap)^alpha), lighter
    than the true tail."""
    return alpha / (1.0 - (kmin / cap) ** alpha)


def censoring_crossing(kmin, cap):
    """The lowest exponent whose naive capped estimate reads 1 or more: the root of a = 1 - (kmin / cap)^a
    in (0, 1), by bisection. Every exponent between it and 1 has no finite mean shortfall and reads as one
    that has."""
    lo, hi = 1e-9, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        lo, hi = (mid, hi) if censored_naive(mid, kmin, cap) < 1.0 else (lo, mid)
    return (lo + hi) / 2.0
