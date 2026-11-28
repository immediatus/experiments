"""Checks Part 6's interaction-order law. A seam's order is the size of its smallest failing set of
mechanisms; that set fails while every proper subset passes, so it is an interaction of exactly that order.
Each seam's smallest failing set has a closed characterization, checked here against brute force over every
subset of random systems:
  signal: with each loop's row scaled to unit self-gain, a set and all its subsets pass the relative-gain
          test exactly when the set's matrix is a P-matrix, every principal minor positive; the order is the
          size of the smallest principal submatrix with a non-positive determinant;
  assumption: the order is the length of the shortest directed cycle of the start-time graph (its girth);
  order: the order is the fewest webhooks that write a fact with more inversions than the passes allow,
         together with every fact it needs;
  state: the order is the fewest informers, heaviest first, whose lists exceed capacity x (mean watch + history).

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import random
import unittest

from formulas import fact_passes, singular_coupling, spread_order, subset_facts, symmetric_gain
from interaction import assumption_order, has_cycle, is_p_matrix, order_order, signal_order, signal_set_passes, state_order


def brute_min_failing(items, fails):
    """The size of the smallest subset of `items` on which `fails` is true, by trying every subset in order of size,
    or None."""
    for k in range(1, len(items) + 1):
        for s in itertools.combinations(items, k):
            if fails(s):
                return k
    return None


def random_gain(n, spread, rng):
    """An n x n gain matrix with unit diagonal and couplings drawn uniformly from [-spread, spread]."""
    return [[1.0 if i == j else rng.uniform(-spread, spread) for j in range(n)] for i in range(n)]


class Signal(unittest.TestCase):
    """P matrix iff every subset passes; order is the smallest failing set; rows scaled by self gain; symmetric
    loops have order n."""

    def test_p_matrix_iff_every_subset_passes(self):
        rng = random.Random(7)
        for _ in range(300):
            n = rng.choice((3, 4, 5))
            g = random_gain(n, 0.9, rng)
            every = all(signal_set_passes(g, s) for k in range(1, n + 1) for s in itertools.combinations(range(n), k))
            self.assertEqual(is_p_matrix(g), every)

    def test_order_is_the_smallest_failing_set(self):
        rng = random.Random(11)
        for _ in range(300):
            n = rng.choice((3, 4, 5))
            g = random_gain(n, 0.95, rng)
            brute = brute_min_failing(range(n), lambda s: not signal_set_passes(g, s))
            self.assertEqual(signal_order(g), brute)

    def test_rows_scaled_by_self_gain(self):
        g = [[-1.0, -1.0], [-1.0, -1.0]]            # Part 1's shared metric: singular, order two
        self.assertEqual(signal_order(g), 2)

    def test_symmetric_loops_have_order_n(self):
        for n in (3, 4, 5, 6):
            self.assertEqual(signal_order(symmetric_gain(n, singular_coupling(n))), n)


class Assumption(unittest.TestCase):
    """Girth is the smallest failing set; a cycle of n has order n."""

    def test_girth_is_the_smallest_failing_set(self):
        rng = random.Random(3)
        for _ in range(300):
            n = rng.choice((4, 5, 6))
            needs = {i: {j for j in range(n) if j != i and rng.random() < 0.3} for i in range(n)}
            brute = brute_min_failing(range(n), lambda s: has_cycle(needs, set(s)))
            self.assertEqual(assumption_order(needs), brute)

    def test_a_cycle_of_n_has_order_n(self):
        for n in (2, 3, 6):
            self.assertEqual(assumption_order({i: {(i + 1) % n} for i in range(n)}), n)


class Order(unittest.TestCase):
    """Closure is the smallest failing set; spread chain has order n."""

    def test_closure_is_the_smallest_failing_set(self):
        rng = random.Random(5)
        checked = 0
        for _ in range(400):
            w = rng.choice((3, 4, 5))
            facts = {}
            for f in range(rng.choice((3, 4, 5, 6))):
                pre = {g for g in facts if rng.random() < 0.5}
                facts[f] = (rng.randrange(w), pre)
            order = list(range(w))
            rng.shuffle(order)

            def fails(s):
                sub = subset_facts(facts, set(s))
                return bool(sub) and fact_passes([x for x in order if x in s], sub) > 2

            brute = brute_min_failing(range(w), fails)
            self.assertEqual(order_order(order, facts), brute)
            checked += brute is not None
        self.assertGreater(checked, 20)

    def test_spread_chain_has_order_n(self):
        for n in (3, 4, 5, 6):
            facts = {i: (i, {i - 1} if i else set()) for i in range(n)}
            self.assertEqual(order_order(spread_order(n), facts), n)


class State(unittest.TestCase):
    """Identical informers; heaviest first."""

    def test_identical_informers(self):
        self.assertEqual(state_order([100.0] * 2000, 100.0, 450.0, 300.0), 751)

    def test_heaviest_first(self):
        self.assertEqual(state_order([50000.0, 30000.0] + [10.0] * 100, 100.0, 450.0, 300.0), 2)


class CorrectedSignalTest(unittest.TestCase):
    """The signal test needs a positive determinant as well as positive relative gains: with unit self-gains a
    loop's relative gain is det(M without it) / det(M), so two negative determinants give a positive gain, and a
    negative determinant makes decentralized integral control unstable (Grosdidier, Morari & Holt 1985)."""

    def test_negative_determinant_fails_although_every_gain_is_positive(self):
        g = [[1.0, 1.5, 1.0], [1.5, 1.0, -2.0], [1.5, -1.0, 1.0]]
        self.assertFalse(signal_set_passes(g, [0, 1, 2]))

    def test_four_symmetric_loops_with_negative_determinant_fail(self):
        self.assertFalse(signal_set_passes(symmetric_gain(4, -0.55), [0, 1, 2, 3]))

    def test_three_loops_that_pass_have_every_pair_passing(self):
        rng = random.Random(3)
        for _ in range(2000):
            g = [[1.0 if i == j else rng.uniform(-2, 2) for j in range(3)] for i in range(3)]
            if signal_set_passes(g, [0, 1, 2]):
                for s in itertools.combinations(range(3), 2):
                    self.assertTrue(signal_set_passes(g, s))

    def test_four_loops_can_pass_while_every_triple_fails(self):
        row = [1.0, 2.0, 2.0, -2.0]
        g = [[row[(j - i) % 4] for j in range(4)] for i in range(4)]
        self.assertTrue(signal_set_passes(g, [0, 1, 2, 3]))
        self.assertFalse(signal_set_passes(g, [0, 2]))
        self.assertFalse(signal_set_passes(g, [1, 3]))
        for s in itertools.combinations(range(4), 3):
            self.assertFalse(signal_set_passes(g, s))


if __name__ == '__main__':
    unittest.main()
