"""Part 3's tail of list costs. Informers list collections of different sizes, and a full trigger's backlog
is the sum of their list costs over capacity. Proposition 21's necessary condition holds for any split of
that sum; the simulated onset (relist.simulate_limited with one cost per client) also sits at one backlog,
about 2,250 seconds in the specimen, for tail exponents from 3 down to 1.5. Over clusters whose informers
draw their costs from one Pareto law of a fixed mean, whether a cluster of N informers storms is then the
event that its sum passes that backlog.
"""
import math
import random


def heterogeneous_storm_possible(costs, capacity, mean_watch, retention):
    """Proposition 21 with one list cost per informer: a saturated storm needs sum(costs) / capacity to
    exceed mean_watch + retention. With a share phi_i of informer i's cycles ending in a list,
    saturation gives sum(phi_i omega_i / E[cycle_i]) = capacity with E[cycle_i] >= mean_watch +
    phi_i retention, and phi / (mean_watch + phi retention) is largest at phi = 1."""
    return math.fsum(costs) / capacity > mean_watch + retention


def pareto_costs(n, alpha, mean, rng):
    """n list costs Pareto with exponent alpha (> 1) and the given mean: scale mean (alpha - 1) / alpha."""
    scale = mean * (alpha - 1.0) / alpha
    return [scale * (1.0 - rng.random()) ** (-1.0 / alpha) for _ in range(n)]


def storm_share(n, alpha, mean=112.5, capacity=100.0, boundary=2250.0, trials=4000, seed=9):
    """Share of clusters of n informers, costs Pareto(alpha) of the given mean, whose full-trigger
    backlog passes the simulated boundary. The mean puts 2,000 informers at the boundary on average."""
    rng = random.Random(seed)
    hits = sum(1 for _ in range(trials) if math.fsum(pareto_costs(n, alpha, mean, rng)) / capacity > boundary)
    return hits / trials
