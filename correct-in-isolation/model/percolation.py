"""Part 4's start-time graph at scale. Components need each other to start; after a full restart a component
starts once everything it needs has started, so the components that never start are exactly those with a
path into a cycle (Proposition 23 with every component down). Graphs are drawn with each edge i -> j, i
needing j, present with probability min(1, c w_i w_j / (n E[w]^2)): weights all equal give independent
degrees of mean c, and Pareto weights give hubs whose in- and out-degrees both grow with one weight. The giant
in-component appears where E[k_in k_out] = E[k] (Dorogovtsev, Mendes and Samukhin 2001), which for these
graphs is c = E[w]^2 / E[w^2].
"""
import math
import sys

from audit import cyclic_components

sys.setrecursionlimit(100000)


def pareto_weights(n, exponent, rng):
    """n component weights drawn from a Pareto distribution above 1 with tail exponent `exponent` (larger is
    lighter-tailed), from the seeded rng; dimensionless multipliers of a component's chance of a dependency."""
    return [(1.0 - rng.random()) ** (-1.0 / exponent) for _ in range(n)]


def gen_needs(c, weights, rng):
    """A start-time graph on len(weights) components with mean degree about c."""
    n = len(weights)
    m = math.fsum(weights) / n
    k = c / (n * m * m)
    return {i: {j for j in range(n) if j != i and rng.random() < min(1.0, k * weights[i] * weights[j])}
            for i in range(n)}


def predicted_threshold(weights):
    """E[w]^2 / E[w^2]: the mean degree at which the giant stranded set appears."""
    n = len(weights)
    return (math.fsum(weights) / n) ** 2 / (math.fsum(w * w for w in weights) / n)


def stranded(needs):
    """Components that never start after a full restart: those with a path into a cycle."""
    unmet = {i: len(needs[i]) for i in needs}
    users = {i: [] for i in needs}
    for i, ds in needs.items():
        for j in ds:
            users.setdefault(j, []).append(i)
            unmet.setdefault(j, len(needs.get(j, ())))
    ready = [i for i, u in unmet.items() if u == 0]
    up = set(ready)
    while ready:
        j = ready.pop()
        for i in users.get(j, ()):
            unmet[i] -= 1
            if unmet[i] == 0:
                up.add(i)
                ready.append(i)
    return set(unmet) - up


def greedy_relaxation(needs):
    """Components whose in-edges a recovery controller relaxes (for a webhook, failurePolicy Ignore while the
    cluster restarts), chosen one at a time from the largest cycle core by the most in- times out-edges within
    it, until no cycle is left. An upper bound on the smallest such set, a feedback vertex set (NP-hard,
    Karp 1972). Returned in the order chosen, so a prefix is a smaller relaxation."""
    g = {a: set(bs) for a, bs in needs.items()}
    relaxed = []
    while True:
        cores = cyclic_components(g)
        if not cores:
            return relaxed
        core = max(cores, key=len)
        indeg = {v: 0 for v in core}
        for a in core:
            for b in g.get(a, ()):
                if b in core:
                    indeg[b] += 1
        x = max(sorted(core, key=str), key=lambda v: indeg[v] * len(g.get(v, set()) & core))
        for a in g:
            g[a].discard(x)
        relaxed.append(x)


def relax(needs, relaxed):
    """The start-time graph with every edge into a relaxed component removed."""
    relaxed = set(relaxed)
    return {a: {b for b in bs if b not in relaxed} for a, bs in needs.items()}


def residual_hidden(needs, hidden, rng):
    """Components still stranded when the controller plans on a graph missing a share `hidden` of the edges,
    as edges no object records (a webhook's need for DNS) are, and its relaxation meets the true graph."""
    visible = {a: {b for b in bs if rng.random() >= hidden} for a, bs in needs.items()}
    return len(stranded(relax(needs, greedy_relaxation(visible))))


def hard_floor(needs, hard, rng):
    """Components stranded however the controller relaxes, when a share `hard` of the edges cannot be relaxed
    (a need for nodes, a network, an image): relaxing every other edge is the best any controller can do,
    so the floor is the stranded set of the hard edges alone."""
    return len(stranded({a: {b for b in bs if rng.random() < hard} for a, bs in needs.items()}))
