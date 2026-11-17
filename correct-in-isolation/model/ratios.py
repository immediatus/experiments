"""Part 6: each seam's ratio of what the composite asks to what it can give. The seam binds when its ratio
passes one; the ratio's dependence on scale says which tests a scaled-down cluster keeps."""
from __future__ import annotations

from typing import Hashable

from audit import cyclic_components
from formulas import rounds, vpa_utilisation

Needs = dict[Hashable, set]  # component -> the components it needs to start


def signal_ratio(u_h: float, margin: float = 0.15, q: float = 1.0, tol_up: float = 0.1, tol_down: float = 0.1) -> float:
    """How far a target lies outside the rest band [v/(1+tol_up), v/(1-tol_down)] at a steady load, with
    v = 1/((1+m) q): the larger of v/((1+tol_up) u_h), above one when the pair drifts up, and
    u_h (1-tol_down)/v, above one when it drifts down."""
    v = vpa_utilisation(margin, q)
    return max(v / ((1.0 + tol_up) * u_h), u_h * (1.0 - tol_down) / v)


def time_ratio(k: float, covered: int = 0, target: float = 0.5, limit: float = 1.0) -> float:
    """Rounds a k-fold surge needs over the rounds free slots cover plus one: above one at least one round
    after the first waits for nodes, the cost of nesting (Propositions 8 and 9)."""
    return rounds(k, target=target, limit=limit) / (covered + 1.0)


def state_ratio(informers: int, cost_list: float, capacity: float, mean_watch: float, retention: float) -> float:
    """The forced backlog N_I omega / kappa over mean_watch + retention: Proposition 21's necessary condition
    for a saturated storm passes one."""
    return informers * cost_list / capacity / (mean_watch + retention)


def order_ratio(passes_needed: int, passes_allowed: int = 2) -> float:
    """The passes an order needs, one plus its most inversions on a path (Proposition 37), over the passes the
    contract allows."""
    return passes_needed / passes_allowed


def scaled_state_ratio(ratio: float, fraction: float, grows: bool) -> float:
    """The state ratio of a test cluster with `fraction` of the nodes and every mechanism kept, at the same
    capacity: informers scale with the nodes, and a list that grows with the cluster (an informer on every pod)
    shrinks with it too, so the ratio falls by fraction, or by fraction squared."""
    return ratio * fraction * (fraction if grows else 1.0)


def assumption_ratio(needs: Needs, tol: float = 1e-10, iterations: int = 200000) -> float:
    """The spectral radius of the start-time graph: zero when it has no cycle, one when its cycles share no
    component, above one where cycles interlock, so that the number of start-time paths grows with their
    length. A reducible graph's radius is the largest over its strongly connected cores. On a core, A + I is
    primitive, and for any positive x the smallest and largest of ((A + I) x)_v / x_v bracket its radius
    (Collatz and Wielandt); power iteration narrows the bracket until it is tol wide."""
    best = 0.0
    for core in cyclic_components(needs):
        nodes = sorted(core, key=str)
        x = {v: 1.0 for v in nodes}
        for _ in range(iterations):
            y = {v: x[v] + sum(x[w] for w in needs.get(v, ()) if w in core) for v in nodes}
            ratios = [y[v] / x[v] for v in nodes]
            lo, hi = min(ratios), max(ratios)
            top = max(y.values())
            x = {v: y[v] / top for v in nodes}
            if hi - lo < tol:
                break
        best = max(best, (lo + hi) / 2.0 - 1.0)
    return best
