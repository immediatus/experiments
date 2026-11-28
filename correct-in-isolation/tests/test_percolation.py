"""Checks Part 4's percolation results. A start-time graph drawn at random, each edge a need, strands after a
full restart every component with a path into a cycle. With independent degrees of mean c a giant stranded
set appears near c = 1; with hubs whose in- and out-degrees both grow with one weight, at
c = E[w]^2 / E[w^2], which is zero for weights without a second moment. A recovery controller relaxes the
in-edges of a few components, chosen greedily from the largest cycle core; edges it cannot see, or cannot
relax, leave components stranded.

Run: python3 -m unittest discover -s tests
"""
import os
import random
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from audit import min_feedback_vertex_set
from percolation import gen_needs, greedy_relaxation, hard_floor, pareto_weights, predicted_threshold, relax, residual_hidden, stranded


def share(c, exponent=None, n=1000, seeds=3):
    """The mean share of components stranded after a full restart of random start-time graphs of n components at
    mean degree c, equal weights or Pareto weights of the given exponent, over `seeds` draws."""
    out = 0
    for seed in range(seeds):
        rng = random.Random(seed)
        w = [1.0] * n if exponent is None else pareto_weights(n, exponent, rng)
        out += len(stranded(gen_needs(c, w, rng)))
    return out / (n * seeds)


class Stranded(unittest.TestCase):
    """Cycle and upstream; mean degree."""

    def test_cycle_and_upstream(self):
        needs = {'a': {'b'}, 'b': {'a'}, 'c': {'a'}, 'd': {'e'}, 'e': set()}
        self.assertEqual(stranded(needs), {'a', 'b', 'c'})

    def test_mean_degree(self):
        rng = random.Random(1)
        needs = gen_needs(1.5, [1.0] * 1000, rng)
        self.assertLess(abs(sum(len(v) for v in needs.values()) / 1000 / 1.5 - 1), 0.05)


class Threshold(unittest.TestCase):
    """Equal weights; pareto weights; independent degrees have a threshold near one; hubs remove it."""

    def test_equal_weights(self):
        self.assertAlmostEqual(predicted_threshold([1.0] * 10), 1.0)

    def test_pareto_weights(self):
        w = pareto_weights(200000, 2.5, random.Random(2))
        self.assertLess(abs(predicted_threshold(w) / (1.0 / 1.8) - 1), 0.15)

    def test_independent_degrees_have_a_threshold_near_one(self):
        self.assertLess(share(0.5), 0.03)
        self.assertGreater(share(2.0), 0.5)

    def test_hubs_remove_it(self):
        self.assertGreater(share(0.5, 1.8), 0.03)


class Relaxation(unittest.TestCase):
    """Greedy frees everything; greedy returns its order; greedy against exact on small graphs; hidden edges leave
    components stranded; hard floor."""

    def test_greedy_frees_everything(self):
        rng = random.Random(3)
        needs = gen_needs(1.5, [1.0] * 500, rng)
        relaxed = greedy_relaxation(needs)
        cut = {a: {b for b in bs if b not in relaxed} for a, bs in needs.items()}
        self.assertEqual(stranded(cut), set())

    def test_greedy_returns_its_order(self):
        rng = random.Random(3)
        needs = gen_needs(1.5, [1.0] * 300, rng)
        order = greedy_relaxation(needs)
        self.assertIsInstance(order, list)
        left = [len(stranded(relax(needs, set(order[:k])))) for k in range(len(order) + 1)]
        self.assertEqual(left[-1], 0)
        self.assertEqual(left, sorted(left, reverse=True))

    def test_greedy_against_exact_on_small_graphs(self):
        for seed in range(30):
            rng = random.Random(100 + seed)
            needs = gen_needs(1.6, [1.0] * 7, rng)
            exact = len(min_feedback_vertex_set(needs))
            greedy = len(greedy_relaxation(needs))
            self.assertGreaterEqual(greedy, exact)
            self.assertLessEqual(greedy, exact + 2)

    def test_hidden_edges_leave_components_stranded(self):
        rng = random.Random(4)
        needs = gen_needs(1.5, [1.0] * 1000, rng)
        self.assertEqual(residual_hidden(needs, 0.0, random.Random(5)), 0)
        self.assertGreater(residual_hidden(needs, 0.2, random.Random(5)), 0)

    def test_hard_floor(self):
        rng = random.Random(6)
        needs = gen_needs(2.0, [1.0] * 1000, rng)
        self.assertEqual(hard_floor(needs, 0.0, random.Random(7)), 0)
        rng = random.Random(6)
        hubs = gen_needs(2.0, pareto_weights(1000, 1.8, rng), rng)
        self.assertGreater(hard_floor(hubs, 0.3, random.Random(7)), hard_floor(needs, 0.3, random.Random(7)))


if __name__ == '__main__':
    unittest.main()
