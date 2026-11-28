"""Checks the hazard rule for a memory kept as pods. The derivative of the expected cost is the
chance the gap is still open times (spare nodes - rate x cold time x hazard), so with a hazard
that does not fall the cheapest window is zero or the cap, and with one that falls it is the
window where the hazard drops to spare / (rate x cold time), capped at an hour. Weibull gaps with
a mean of 1800 s stand in for the three shapes.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import WINDOW_CAP, hazard_window, weibull_pod_cost, weibull_scale
from nested import simulate_two_surges

SPARE, POD, NODE, K, MEAN = 58, 90, 210, 30, 1800


def grid_best(shape, rate):
    """The pod window, on a 10-second grid up to the hour cap, with the least expected cost for Weibull gaps of the
    given shape and an exchange rate."""
    return min(range(0, WINDOW_CAP + 1, 10), key=lambda m: weibull_pod_cost(m, shape, MEAN, rate, K, POD, NODE, SPARE))


class HazardRule(unittest.TestCase):
    """Scale gives the mean; falling hazard has an interior window; the cap binds when the window would pass an
    hour; a hazard that does not fall gives zero or the cap; simulated cost is lowest at the hazard window."""

    def test_scale_gives_the_mean(self):
        for shape in (0.5, 1.0, 3.0):
            self.assertAlmostEqual(weibull_scale(MEAN, shape) * math.gamma(1 + 1 / shape), MEAN)

    def test_falling_hazard_has_an_interior_window(self):
        for shape, rate in ((0.5, 16), (0.5, 64), (0.7, 64), (0.5, 160)):
            w = hazard_window(shape, MEAN, rate, K, POD, NODE, SPARE)
            self.assertTrue(0 < w < WINDOW_CAP, (shape, rate, w))
            self.assertLessEqual(abs(grid_best(shape, rate) - w), 10, (shape, rate, w))

    def test_the_cap_binds_when_the_window_would_pass_an_hour(self):
        self.assertEqual(hazard_window(0.7, MEAN, 160, K, POD, NODE, SPARE), WINDOW_CAP)
        self.assertEqual(grid_best(0.7, 160), WINDOW_CAP)

    def test_a_hazard_that_does_not_fall_gives_zero_or_the_cap(self):
        for shape in (1.0, 1.5, 3.0):
            self.assertIsNone(hazard_window(shape, MEAN, 64, K, POD, NODE, SPARE))
            for rate in (16, 64, 160):
                self.assertIn(grid_best(shape, rate), (0, WINDOW_CAP), (shape, rate))

    def test_simulated_cost_is_lowest_at_the_hazard_window(self):
        shape, rate, n = 0.5, 64, 300
        eta = weibull_scale(MEAN, shape)
        gaps = [eta * (-math.log(1 - (i + 0.5) / n)) ** (1 / shape) for i in range(n)]
        w = round(hazard_window(shape, MEAN, rate, K, POD, NODE, SPARE))
        def cost(m):
            runs = [simulate_two_surges(g, stabilization=m, unneeded=0, bulk=10 ** 6) for g in gaps]
            return sum(h + rate * t for t, h in runs) / n
        at_w = cost(w)
        self.assertLess(at_w, cost(0))
        self.assertLess(at_w, cost(WINDOW_CAP))


if __name__ == '__main__':
    unittest.main()
