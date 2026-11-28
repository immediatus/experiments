"""Checks Part 3's tail result. A saturated storm needs the total work of a full trigger, the sum of every
informer's list cost over capacity, to pass the mean watch plus the history, however the work is split.
With list costs Pareto of a fixed mean, whether a cluster of N informers passes the simulated boundary is
then a question about a sum of heavy-tailed costs: the heavier the tail, the wider the range of cluster
sizes over which some clusters storm and others do not.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import random
import unittest

from tail_lists import heterogeneous_storm_possible, pareto_costs, storm_share


class Necessary(unittest.TestCase):
    """Uniform costs reduce to the known condition; split does not matter."""

    def test_uniform_costs_reduce_to_the_known_condition(self):
        self.assertFalse(heterogeneous_storm_possible([37.0] * 2000, 100.0, 450.0, 300.0))
        self.assertTrue(heterogeneous_storm_possible([38.0] * 2000, 100.0, 450.0, 300.0))

    def test_split_does_not_matter(self):
        costs = [10.0] * 1000 + [66.0] * 1000
        self.assertTrue(heterogeneous_storm_possible(costs, 100.0, 450.0, 300.0))


class Costs(unittest.TestCase):
    """Mean is the target."""

    def test_mean_is_the_target(self):
        c = pareto_costs(200000, 1.5, 112.5, random.Random(3))
        self.assertLess(abs(sum(c) / len(c) / 112.5 - 1), 0.05)


class Share(unittest.TestCase):
    """Light tail is a step; heavy tail spreads the step; share grows with size."""

    def test_light_tail_is_a_step(self):
        self.assertEqual(storm_share(1800, 3.0, trials=500), 0.0)
        self.assertEqual(storm_share(2200, 3.0, trials=500), 1.0)

    def test_heavy_tail_spreads_the_step(self):
        self.assertGreater(storm_share(1000, 1.2, trials=1000), 0.01)
        self.assertLess(storm_share(2500, 1.2, trials=1000), 0.7)

    def test_share_grows_with_size(self):
        xs = [storm_share(n, 1.5, trials=1000) for n in (1500, 2000, 2500)]
        self.assertEqual(xs, sorted(xs))


if __name__ == '__main__':
    unittest.main()
