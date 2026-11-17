"""Checks Part 2's frontier in slots. With H free slots a round is covered when the pods it adds fit in them,
min(n0 g^j, N*) - n0 <= H, so a slot short of a whole round still covers the last round of every surge small
enough. Over Pareto surge sizes the mean shortfall falls a little with each such slot, and drops in a jump at
each whole round's price n0 (g^c - 1), where the round is covered for every larger surge at once: a staircase
with sloping treads, never above the whole-round values.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import pareto_shortfall, pareto_shortfall_slots, ramp_shortfall


def grid(alpha, n=40000, kmin=2.0):
    return [kmin * (1.0 - (i + 0.5) / n) ** (-1.0 / alpha) for i in range(n)]


class Slots(unittest.TestCase):

    def test_ramp_with_slots(self):
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 210, slots=0), ramp_shortfall(30, 16, 90, 210))
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 210, slots=10 ** 6), ramp_shortfall(30, 16, 90, 0))
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 210, slots=16), ramp_shortfall(30, 16, 90, 210, c=1))

    def test_closed_form_against_grid(self):
        for alpha in (2.5, 3.0):
            ks = grid(alpha)
            for h in (0, 10, 16, 40, 100):
                mean = math.fsum(ramp_shortfall(k, 16, 90, 210, slots=h) for k in ks) / len(ks)
                self.assertLess(abs(mean / pareto_shortfall_slots(alpha, 16, 90, 210, h) - 1), 0.02)

    def test_staircase_with_sloping_treads(self):
        steps = {16 * (2 ** c - 1) for c in range(1, 6)}
        for alpha in (1.5, 2.0):
            prev = pareto_shortfall_slots(alpha, 16, 90, 210, 0)
            self.assertAlmostEqual(prev, pareto_shortfall(alpha, 16, 90, 210))
            for h in range(1, 500):
                v = pareto_shortfall_slots(alpha, 16, 90, 210, h)
                self.assertLessEqual(v, prev + 1e-9)
                if h in steps:
                    self.assertGreater(prev - v, 0.04 * prev)
                else:
                    self.assertLess(prev - v, 0.01 * prev)
                prev = v
            for c in (1, 2, 3):
                self.assertLessEqual(pareto_shortfall_slots(alpha, 16, 90, 210, 16 * (2 ** c - 1)),
                                     pareto_shortfall(alpha, 16, 90, 210, c) + 1e-9)


if __name__ == '__main__':
    unittest.main()
