"""Checks the unknown-gap extension of Part 2's model. With memoryless gaps between surges the
expected cost of an unneeded time, node-time held plus an exchange rate times the second surge's
time, is lowest at zero or at infinity and never between, with the switch where the spare nodes
held through a mean gap cost as much as every round's node wait. Against the worst gap, holding
for the break-even time costs less than twice what knowing the gap would, when the pod loop's
window outlasts the ramp.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import break_even, expected_held, expected_time, gap_cost, hold_through, rounds, second_surge_time, worst_ratio
from nested import simulate_two_surges

SPARE, S, POD, NODE, K = 58, 300, 90, 210, 30
FOREVER = 10 ** 9


def quadrature(f, mu, n=20000):
    """Mean of f(G) for G exponential with mean mu, by the midpoint rule on quantiles."""
    return sum(f(-mu * math.log(1 - (i + 0.5) / n)) for i in range(n)) / n


class UnknownGap(unittest.TestCase):
    """Expected forms match quadrature; memoryless optimum is zero or forever; break even is less than twice the
    hindsight cost; simulated means follow the closed form."""

    def test_expected_forms_match_quadrature(self):
        for mu in (600, 1800):
            for u in (0, 300, 600, 1800):
                held = quadrature(lambda g: SPARE * min(g, S + u), mu)
                time = quadrature(lambda g: second_surge_time(g, K, POD, NODE, S, u), mu)
                self.assertAlmostEqual(expected_held(u, mu, SPARE, S), held, delta=0.002 * held)
                self.assertAlmostEqual(expected_time(u, mu, K, POD, NODE, S), time, delta=0.5)

    def test_memoryless_optimum_is_zero_or_forever(self):
        for mu in (300, 600, 1800, 7200):
            for lam in (1, 4, 16, 41, 42, 64, 256, 1024):
                def cost(u):
                    return gap_cost(u, mu, lam, K, POD, NODE, SPARE, S)
                ends = min(cost(0), cost(FOREVER))
                for u in range(30, 30001, 30):
                    self.assertGreaterEqual(cost(u), ends - 1e-6, (mu, lam, u))
                self.assertEqual(cost(FOREVER) < cost(0), hold_through(mu, lam, K, NODE, SPARE), (mu, lam))

    def test_break_even_is_less_than_twice_the_hindsight_cost(self):
        self.assertGreaterEqual(S, (rounds(K) - 1) * POD)
        for lam in (4, 16, 64, 256):
            u = break_even(lam, K, NODE, SPARE)
            self.assertAlmostEqual(u, lam * rounds(K) * NODE / SPARE)
            self.assertLess(worst_ratio(u, lam, K, POD, NODE, SPARE, S), 2)

    def test_simulated_means_follow_the_closed_form(self):
        for mu, u in ((600, 0), (600, 600), (1800, FOREVER)):
            n = 120
            runs = [simulate_two_surges(-mu * math.log(1 - (i + 0.5) / n), unneeded=u, bulk=10 ** 6) for i in range(n)]
            time = sum(t for t, _ in runs) / n
            closed = expected_time(min(u, 10 ** 7), mu, K, POD, NODE, S)
            self.assertLess(abs(time - closed), 40, (mu, u, time, closed))


if __name__ == '__main__':
    unittest.main()
