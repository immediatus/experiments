"""Checks Part 1's transition and frontier. The drift rate, ln F over the step interval, is positive down to
the band's low edge, where F = 1 + tol, and zero above it: a jump, not a slope. The highest target that can
rest at some margin of at least zero is 1 / (q (1 - tol)), which falls with the tail and crosses 0.5 near
sigma = 1.28 on a lognormal factor.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import drift_rate, lognormal_q, max_resting_target, step_factor


class Transition(unittest.TestCase):

    def test_jump_at_the_edge(self):
        edge = 1.0 / (1.15 * 1.1)
        below, above = drift_rate(edge - 1e-6), drift_rate(edge + 1e-6)
        self.assertAlmostEqual(below, math.log(1.1) / (24 * math.log2(10)), places=6)
        self.assertEqual(above, 0.0)

    def test_rate_is_ln_step_over_interval(self):
        self.assertAlmostEqual(drift_rate(0.5), math.log(step_factor(0.5)) / (24 * math.log2(10)))


class Frontier(unittest.TestCase):

    def test_light_tail_allows_any_target(self):
        self.assertGreater(max_resting_target(lognormal_q(0.0)), 1.0)

    def test_heavy_tail_caps_the_target(self):
        self.assertLess(max_resting_target(lognormal_q(1.2816)), 0.5)
        self.assertAlmostEqual(max_resting_target(lognormal_q(1.2816)), 1 / (lognormal_q(1.2816) * 0.9))


if __name__ == '__main__':
    unittest.main()
