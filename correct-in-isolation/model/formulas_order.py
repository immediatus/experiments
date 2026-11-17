"""Closed forms of Part 5, a shared order: passes an enabling chain needs, the Eulerian share of orders that
converge, value and match links, the passes of a general fact graph, and mixed images under per-pod pinning.

Every input is a documented contract or a named parameter; defaults are the series' specimen."""
import itertools
import math



def eulerian(n, k):
    """Eulerian number A(n, k): permutations of n items with exactly k descents."""
    return sum((-1) ** j * math.comb(n + 1, j) * (k + 1 - j) ** n for j in range(k + 2))


def passes_needed(order_positions):
    """Passes an enabling chain needs in a given order: one, plus one for every webhook placed
    before the webhook that enables it. order_positions[i] is the position of chain member i."""
    return 1 + sum(order_positions[i] < order_positions[i - 1] for i in range(1, len(order_positions)))


def converged_share(n, passes):
    """Share of the n! orders of an n-member enabling chain that reach the common fixed point
    within `passes` passes, if every order is equally likely: sum of A(n, k) for k < passes, over
    n!. Two passes, the reinvocation contract: (2^n - n) / n!."""
    return sum(eulerian(n, k) for k in range(min(passes, n))) / math.factorial(n)


def never_share(n, eta):
    """Share of the n! orders of an n-member chain of value links that reach the common fixed point
    within the contract's two passes when the member at position eta (counting the first as zero)
    is the last whose configuration sets reinvocationPolicy Never, every other member IfNeeded. A
    Never member is called once, so for convergence it acts as a match link into it: the members
    up to eta must stand in chain order, and the links after it may hold one inversion between them.
    Read in chain order, the members' positions then have at most one descent, and none before
    eta: one order with none, and C(n, k) - 1 with a single descent after the first k members, for
    k from eta + 1 to n - 1. eta = 0 gives (2^n - n) / n!; eta = n - 1 gives 1 / n!."""
    return (1 + sum(math.comb(n, k) - 1 for k in range(eta + 1, n))) / math.factorial(n)


def mix_share(n, q):
    """Expected two-pass share of an n-member value chain's orders that converge when each member
    after the first keeps reinvocationPolicy Never independently with probability q (the head waits
    for no one, so its setting does not matter): the last Never member stands at position eta with
    probability q (1 - q)^(n - 1 - eta) for eta >= 1, and none keeps it with probability
    (1 - q)^(n - 1)."""
    total = (1 - q) ** (n - 1) * never_share(n, 0)
    for eta in range(1, n):
        total += q * (1 - q) ** (n - 1 - eta) * never_share(n, eta)
    return total


def typed_chain_rounds(kinds, order_positions):
    """The round in which the last member of a typed chain acts, or None if some member never
    acts. Member 0 acts in round 0. Across a value link, member i + 1 acts in member i's round, or
    one round later if it is placed before member i. Across a match link, member i + 1 is called
    at all only if member i acted in round 0, before it."""
    r = 0
    for i, kind in enumerate(kinds):
        before = order_positions[i + 1] < order_positions[i]
        if kind == 'value':
            r += before
        elif r > 0 or before:
            return None
    return r


def typed_chain_share(kinds, passes):
    """Share of the orders of a chain with value and match links that reach the common fixed
    point within `passes` rounds, every order equally likely. With value links only it is
    converged_share; with match links only it is 1 / n! at any number of passes."""
    n = len(kinds) + 1
    hits = 0
    for perm in itertools.permutations(range(n)):
        r = typed_chain_rounds(kinds, perm)
        hits += r is not None and r < passes
    return hits / math.factorial(n)


def match_ceiling(kinds):
    """Share of orders of a typed chain that converge at any number of rounds: 1 / (m + 2)!, m the
    index of the last match link, since members 0 to m + 1 must stand in chain order and the value
    links after them converge in any order given rounds enough; 1 with no match link."""
    last = max((i for i, k in enumerate(kinds) if k == 'match'), default=None)
    return 1.0 if last is None else 1 / math.factorial(last + 2)


def fact_passes(order, facts):
    """Passes an order of mutating webhooks needs to reach the common fixed point, every webhook
    IfNeeded and reinvoked whenever the object changed after its call. facts maps each fact to
    (the webhook that writes it, the facts it needs). A fact with no prerequisites appears in pass
    one; a fact appears in the pass of its last prerequisite, or one later if its writer stands
    before that prerequisite's writer. The answer is one plus the most inversions along any path."""
    pos = {w: i for i, w in enumerate(order)}
    memo = {}

    def rank(f):
        if f not in memo:
            writer, prereqs = facts[f]
            memo[f] = max((rank(g) + (pos[writer] < pos[facts[g][0]]) for g in prereqs), default=0)
        return memo[f]
    return 1 + max((rank(f) for f in facts), default=0)


def subset_facts(facts, keep):
    """The facts a subset of the webhooks can still write: those whose writer is kept and whose
    prerequisites, followed back, are all written by kept webhooks. A fact whose prerequisite has no
    writer in the subset never appears, so a check of the subset never sees it."""
    out = {}
    pending = dict(facts)
    changed = True
    while changed:
        changed = False
        for f, (writer, prereqs) in list(pending.items()):
            if writer in keep and all(g in out for g in prereqs):
                out[f] = (writer, set(prereqs))
                del pending[f]
                changed = True
    return out


def time_to_mixed(tag_rate, replace_rate):
    """Mean time until a ReplicaSet whose pods are pinned to a digest one by one, at creation, runs
    two images: the tag moves first (rate tag_rate), then a pod is replaced (rate replace_rate) and
    resolves the new digest. Both clocks are memoryless, so the mean is the sum of the two means."""
    return 1.0 / tag_rate + 1.0 / replace_rate


def mixed_within(tag_rate, replace_rate, horizon):
    """Probability that the ReplicaSet of time_to_mixed runs two images within the horizon: the
    distribution function of a sum of two exponential times."""
    a, b, h = tag_rate, replace_rate, horizon
    if abs(a - b) < 1e-12:
        return 1.0 - math.exp(-a * h) * (1.0 + a * h)
    return 1.0 - (b * math.exp(-a * h) - a * math.exp(-b * h)) / (b - a)
