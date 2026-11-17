"""Part 6: the order of an interaction, computed for each seam. A seam's order is the size of the smallest
set of mechanisms whose seam test fails. That set fails while every proper subset passes (a smaller failing
set would be smaller still), so it is an interaction of exactly that order, and a check of every subset of a
smaller size passes the system. Each function returns that size, or None when no set fails.
"""
from __future__ import annotations

import itertools
from typing import Hashable, Iterable, Optional

from audit import relative_gains

Matrix = list[list[float]]
Needs = dict[Hashable, set]  # component -> the components it needs to start
Facts = dict[str, tuple[str, set]]  # fact -> (the webhook that writes it, the facts it needs)


def normalized_gains(g: Matrix, s: Iterable[int]) -> Matrix:
    """The submatrix of the loops in s, each row divided by its loop's own gain. Relative gains do not
    change when a loop's output is rescaled, so the test is the same, and every self-gain becomes 1."""
    s = list(s)
    return [[g[i][j] / g[i][i] for j in s] for i in s]


def determinant(m: Matrix) -> float:
    """The determinant of a square matrix by Gaussian elimination with partial pivoting; zero when a pivot
    falls below 1e-12, which the tests read as singular."""
    n = len(m)
    a = [list(map(float, row)) for row in m]
    d = 1.0
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        if abs(a[p][c]) < 1e-12:
            return 0.0
        if p != c:
            a[c], a[p] = a[p], a[c]
            d = -d
        d *= a[c][c]
        for r in range(c + 1, n):
            f = a[r][c] / a[c][c]
            a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return d


def signal_set_passes(g: Matrix, s: Iterable[int]) -> bool:
    """The signal seam's test on the loops in s: with every self-gain scaled to one, the determinant is positive
    and every relative gain is positive. Positive relative gains alone are not enough: a loop's relative gain is
    det(M without it) / det(M), so two negative determinants give a positive gain, and a negative determinant
    makes decentralized integral control unstable (Grosdidier, Morari & Holt 1985)."""
    m = normalized_gains(g, s)
    if determinant(m) <= 1e-12:
        return False
    rga = relative_gains(m)
    return all(rga[i][i] > 0 for i in range(len(m)))


def is_p_matrix(g: Matrix) -> bool:
    """Every principal minor of the normalized matrix positive. With unit self-gains a loop's relative gain is
    det(G without it) / det(G), so by induction from single loops every subset passes the signal test exactly
    when every principal minor is positive."""
    n = len(g)
    return all(determinant(normalized_gains(g, s)) > 1e-12 for k in range(1, n + 1) for s in itertools.combinations(range(n), k))


def signal_order(g: Matrix) -> Optional[int]:
    """Size of the smallest principal submatrix, rows scaled to unit self-gain, with a non-positive
    determinant: the smallest set of loops the signal test fails. Found by enumeration, which is all one can
    promise in general: deciding whether a matrix is a P-matrix is co-NP-complete (Coxson 1994)."""
    n = len(g)
    for k in range(1, n + 1):
        for s in itertools.combinations(range(n), k):
            if determinant(normalized_gains(g, s)) <= 1e-12:
                return k
    return None


def has_cycle(needs: Needs, keep: set) -> bool:
    """Whether the start-time graph restricted to the components in keep has a directed cycle: by Proposition
    23, the set is stranded by a failure of every replica exactly when it does."""
    state = {}

    def visit(u):
        state[u] = 1
        for v in needs.get(u, ()):
            if v in keep and (state.get(v) == 1 or (v not in state and visit(v))):
                return True
        state[u] = 2
        return False
    return any(u not in state and visit(u) for u in keep)


def assumption_order(needs: Needs) -> Optional[int]:
    """The girth of the start-time graph: the length of its shortest directed cycle, found by a breadth-first
    search from every component, O(V (V + E)). Any cycle's components fail together; a set with no cycle
    recovers, so no smaller set fails."""
    best = None
    for s in needs:
        dist, frontier = {s: 0}, [s]
        while frontier:
            nxt = []
            for u in frontier:
                for v in needs.get(u, ()):
                    if v == s:
                        best = dist[u] + 1 if best is None else min(best, dist[u] + 1)
                    elif v not in dist:
                        dist[v] = dist[u] + 1
                        nxt.append(v)
            frontier = nxt
    return best


def order_order(order: list, facts: Facts, passes: int = 2) -> Optional[int]:
    """The smallest set of webhooks whose admission, in the order it inherits, needs more passes than allowed.
    A failing set must write some fact f whose rank (Proposition 37) reaches `passes`, and to write f at all it
    must keep the writer of every fact f needs, followed back; that closure already gives f its full rank,
    because the rank depends only on those facts and the order. So the order of the seam is the least, over
    the facts of rank at least `passes`, number of writers in the fact's closure. Linear in the facts and their
    prerequisites once the ranks are known."""
    pos = {w: i for i, w in enumerate(order)}
    rank, anc = {}, {}

    def r(f):
        if f not in rank:
            writer, pre = facts[f]
            rank[f] = max((r(g) + (pos[writer] < pos[facts[g][0]]) for g in pre), default=0)
            a = {f}
            for g in pre:
                r(g)
                a |= anc[g]
            anc[f] = a
        return rank[f]
    best = None
    for f in facts:
        if r(f) >= passes:
            k = len({facts[x][0] for x in anc[f]})
            best = k if best is None else min(best, k)
    return best


def state_order(costs: list[float], capacity: float, mean_watch: float, retention: float) -> Optional[int]:
    """The fewest informers whose full trigger can saturate the server: Proposition 22 needs the summed list
    work over the capacity to pass mean_watch + retention, so the smallest such set takes the heaviest lists
    first."""
    need = capacity * (mean_watch + retention)
    total = 0.0
    for k, c in enumerate(sorted(costs, reverse=True), 1):
        total += c
        if total > need:
            return k
    return None
