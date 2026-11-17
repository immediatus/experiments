"""Closed forms of Part 6, the whole: symmetric loops whose every proper subset passes while the whole is
singular, the spread order of a chain, and the order of the shared state counted in informers.

Every input is a documented contract or a named parameter; defaults are the series' specimen."""
import math



def symmetric_gain(k, a):
    """Gain matrix of k loops, each with unit gain on its own output and coupling a to every other."""
    return [[1.0 if i == j else a for j in range(k)] for i in range(k)]


def singular_coupling(k):
    """The coupling at which k symmetric loops become singular: the matrix (1 - a) I + a J has
    eigenvalues 1 - a and 1 + (k - 1) a, so it is singular at a = -1 / (k - 1). Every m < k of the
    loops are singular only at -1 / (m - 1), so at this coupling every proper subset is regular."""
    return -1.0 / (k - 1)


def subset_gain(m, a):
    """Relative gain of one loop among m symmetric loops with coupling a: the diagonal of the
    inverse of (1 - a) I + a J is (1 - a / (1 + (m - 1) a)) / (1 - a). At the coupling where k
    loops are singular, k - 1 of them show 2 (k - 1) / k, below 2 for every k."""
    return (1.0 - a / (1.0 + (m - 1) * a)) / (1.0 - a)


def pair_gain_at_singular(k):
    """The relative gain a pair of the k loops shows, 1 / (1 - a^2), at the coupling where the
    k loops together are singular. It falls toward 1 as k grows."""
    a = singular_coupling(k)
    return 1.0 / (1.0 - a * a)


def spread_order(k):
    """An order of a k-member value chain with exactly two inversions, on its first and its last
    link: members 1, 0, 2, ..., k - 3, k - 1, k - 2 (for k = 3, the chain reversed). The whole needs
    three passes; every proper subset, in the order it inherits, needs at most two."""
    if k == 3:
        return [2, 1, 0]
    return [1, 0] + list(range(2, k - 2)) + [k - 1, k - 2]


def informers_to_bind(threshold, cost_list, capacity):
    """The fewest informers whose forced lists build a backlog B = N_I * cost_list / capacity above
    the threshold: the order, counted in clients, of the shared-state seam."""
    return math.floor(threshold * capacity / cost_list) + 1
