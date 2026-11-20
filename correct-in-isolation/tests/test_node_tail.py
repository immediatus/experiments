"""Checks the lagged rule for a memory kept as nodes past the pod window's cap. With the window at
3600 s, the derivative of the expected cost in the deletion time D is spare x survival(D) minus
rate x node wait x the gap's density at D, D - pod, ..., one term per round placed after deletion.
With exponential gaps it is Proposition 11; with a falling hazard the cost has at most one interior
minimum once every round's term is active, while the first (R - 1) pod dead times can hold more.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import WINDOW_CAP, expected_held, expected_time, node_tail_cost, node_tail_slope, rounds

SPARE, POD, NODE, K = 58, 90, 210, 30
RAMP = (rounds(K) - 1) * POD


class NodeTail(unittest.TestCase):

    def test_exponential_gaps_give_proposition_9(self):
        for u in (0, 600, 3600):
            closed = expected_held(u, 1800, SPARE, WINDOW_CAP) + 64 * expected_time(u, 1800, K, POD, NODE, WINDOW_CAP)
            self.assertAlmostEqual(node_tail_cost(u, 1.0, 1800, 64, K, POD, NODE, SPARE), closed, delta=1e-3 * closed)

    def test_the_slope_is_the_derivative(self):
        for shape, mean, rate in ((0.5, 3600, 500), (0.7, 7200, 1000)):
            for u in (50, 400, 5000):
                num = (node_tail_cost(u + 1, shape, mean, rate, K, POD, NODE, SPARE)
                       - node_tail_cost(u - 1, shape, mean, rate, K, POD, NODE, SPARE)) / 2
                self.assertAlmostEqual(node_tail_slope(u, shape, mean, rate, K, POD, NODE, SPARE), num, delta=0.02 * abs(num) + 0.05)

    def test_one_crossing_once_every_round_is_active(self):
        for shape, mean, rate in ((0.5, 7200, 1000), (0.5, 3600, 500), (0.7, 7200, 1000), (0.5, 7200, 500)):
            slope = [node_tail_slope(u, shape, mean, rate, K, POD, NODE, SPARE) for u in range(RAMP + 10, 60000, 10)]
            ups = sum(1 for a, b in zip(slope, slope[1:]) if a < 0 <= b)
            self.assertLessEqual(ups, 1, (shape, mean, rate))

    def test_the_ramp_can_add_a_local_minimum(self):
        slope = [node_tail_slope(u, 0.5, 7200, 1000, K, POD, NODE, SPARE) for u in range(10, 60000, 10)]
        ups = [u for u, (a, b) in zip(range(20, 60000, 10), zip(slope, slope[1:])) if a < 0 <= b]
        self.assertEqual(len(ups), 2)
        self.assertLess(ups[0], RAMP)


if __name__ == '__main__':
    unittest.main()
