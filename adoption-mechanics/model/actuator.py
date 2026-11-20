"""The actuator stage: veto players and the hysteresis band.

Vetoes (Tsebelis 1995). Each veto player has Euclidean preferences around an ideal point in the plane and
accepts a change only if it is strictly closer to their ideal point than the status quo is. The set of
changes all of them accept is the intersection of open disks that each have the status quo on their
boundary; it is empty exactly when the status quo lies in the closed convex hull of the ideal points. On the
hull's boundary the disks touch only at the status quo itself.

Hysteresis. The successor's merit advantage x follows a random walk with step standard deviation sigma per
period. Running the incumbent earns 0, running the successor earns x, weighted by loss_aversion when x < 0.
Switching in either direction costs c_switch, sunk. With loss_on='switch' the weight applies instead to
the cost of leaving the status quo (Samuelson and Zeckhauser 1988; Kahneman, Knetsch and Thaler 1991). Future payoffs are discounted by `discount`. Value
iteration on a grid gives the threshold above which an organization on the incumbent adopts and the one below
which an organization on the successor abandons it; their difference is the hysteresis band.
"""
import math


def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def in_hull(point: tuple[float, float], points: list[tuple[float, float]], eps: float = 1e-12) -> bool:
    """Whether `point` lies in the closed convex hull of `points` (one point, a segment, or a polygon)."""
    hull = _hull(points)
    if len(hull) == 1:
        return abs(point[0] - hull[0][0]) <= eps and abs(point[1] - hull[0][1]) <= eps
    if len(hull) == 2:
        a, b = hull
        if abs(_cross(a, b, point)) > eps * max(1.0, abs(b[0] - a[0]) + abs(b[1] - a[1])):
            return False
        return (min(a[0], b[0]) - eps <= point[0] <= max(a[0], b[0]) + eps
                and min(a[1], b[1]) - eps <= point[1] <= max(a[1], b[1]) + eps)
    return all(_cross(hull[i], hull[(i + 1) % len(hull)], point) >= -eps for i in range(len(hull)))


def win_set_nonempty(sq: tuple[float, float], ideals: list[tuple[float, float]]) -> bool:
    """Whether some change is strictly preferred to the status quo `sq` by every veto player with an ideal
    point in `ideals`."""
    return not in_hull(sq, ideals)


def setter_proposal(sq: tuple[float, float], ideals: list[tuple[float, float]], setter: int,
                    sweeps: int = 20000, tol: float = 1e-13) -> tuple[float, float]:
    """The change a gate proposes when it sets the agenda (Tsebelis 2002, after Romer and Rosenthal 1978): the
    point of the closed win-set of `sq` closest to its own ideal point, ideals[setter]. The closed win-set is the
    intersection of the disks around each ideal point through the status quo; the point is the projection of the
    setter's ideal onto it, by Dykstra's alternating projections, which converge to the exact projection. No change
    beats the result for every gate, so it lies in the closed convex hull of the ideal points and ends all further
    change."""
    radii = [math.hypot(sq[0] - z[0], sq[1] - z[1]) for z in ideals]
    x = list(ideals[setter])
    inc = [[0.0, 0.0] for _ in ideals]
    for _ in range(sweeps):
        moved = 0.0
        for i, (z, r) in enumerate(zip(ideals, radii)):
            y = (x[0] + inc[i][0], x[1] + inc[i][1])
            d = math.hypot(y[0] - z[0], y[1] - z[1])
            p = y if d <= r else (z[0] + (y[0] - z[0]) * r / d, z[1] + (y[1] - z[1]) * r / d)
            inc[i] = [y[0] - p[0], y[1] - p[1]]
            moved = max(moved, abs(p[0] - x[0]), abs(p[1] - x[1]))
            x = [p[0], p[1]]
        if moved < tol:
            break
    return x[0], x[1]


def _root(xs: list[float], margin: list[float]) -> float:
    for i in range(len(xs) - 1):
        a, b = margin[i], margin[i + 1]
        if a <= 0.0 < b or a < 0.0 <= b:
            return xs[i] + (xs[i + 1] - xs[i]) * (-a / (b - a)) if b != a else xs[i]
    raise ValueError('the decision margin does not cross zero on the grid; widen the grid')


def hysteresis_band(c_switch: float, loss_aversion: float, sigma: float, discount: float,
                    grid: int = 161, span: float = 6.0, tol: float = 1e-9, loss_on: str = 'flow') -> tuple[float, float]:
    """The abandon and adopt thresholds (low, high) of merit advantage, in the units of sigma's walk. Inputs:
    sunk switching cost, loss-aversion weight >= 1, per-period step deviation, discount factor in (0, 1), grid
    size and half-width `span` in units of sigma. Thresholds are the interpolated zeros of each decision
    margin, so a zero cost gives a zero band exactly. loss_on says where loss aversion applies: 'flow' weights the
    periods in which the successor trails the incumbent; 'switch' weights the sunk cost of leaving the status
    quo (status-quo bias), so adopting costs loss_aversion * c_switch and abandoning costs c_switch."""
    if loss_on not in ('flow', 'switch'):
        raise ValueError("loss_on must be 'flow' or 'switch', got %r" % loss_on)
    if loss_on == 'switch':
        u_weight, adopt_cost = 1.0, loss_aversion * c_switch
    else:
        u_weight, adopt_cost = loss_aversion, c_switch
    half = span * sigma
    dx = 2.0 * half / (grid - 1)
    xs = [-half + i * dx for i in range(grid)]
    reach = int(3.0 * sigma / dx)
    w = [math.exp(-((k * dx) ** 2) / (2.0 * sigma * sigma)) for k in range(-reach, reach + 1)]
    total = math.fsum(w)
    w = [v / total for v in w]
    u = [x if x >= 0.0 else u_weight * x for x in xs]

    def expect(v):
        out = []
        for i in range(grid):
            out.append(math.fsum(w[k + reach] * v[min(grid - 1, max(0, i + k))] for k in range(-reach, reach + 1)))
        return out

    va, vb = [0.0] * grid, [0.0] * grid
    for _ in range(20000):
        ea, eb = expect(va), expect(vb)
        stay_a = [discount * e for e in ea]
        run_b = [u[i] + discount * eb[i] for i in range(grid)]
        na = [max(stay_a[i], run_b[i] - adopt_cost) for i in range(grid)]
        nb = [max(run_b[i], stay_a[i] - c_switch) for i in range(grid)]
        diff = max(max(abs(na[i] - va[i]), abs(nb[i] - vb[i])) for i in range(grid))
        va, vb = na, nb
        if diff < tol:
            break
    ea, eb = expect(va), expect(vb)
    adopt_margin = [(u[i] + discount * eb[i] - adopt_cost) - discount * ea[i] for i in range(grid)]
    stay_margin = [(u[i] + discount * eb[i]) - (discount * ea[i] - c_switch) for i in range(grid)]
    return _root(xs, stay_margin), _root(xs, adopt_margin)


def band_exponent(costs: list[float], **kw) -> float:
    """Least-squares slope of ln(band width) against ln(cost) over `costs`; keyword arguments go to
    hysteresis_band. Reported by the sections, not assumed."""
    pts = []
    for c in costs:
        lo, hi = hysteresis_band(c, **kw)
        pts.append((math.log(c), math.log(hi - lo)))
    mx = math.fsum(p[0] for p in pts) / len(pts)
    my = math.fsum(p[1] for p in pts) / len(pts)
    return (math.fsum((p[0] - mx) * (p[1] - my) for p in pts)
            / math.fsum((p[0] - mx) ** 2 for p in pts))
