"""Checks Part 1's autonomic supervisor: every supervisor_h hours it estimates q from the vertical loop's
own histogram and sets the margin to 1 / (target q) - 1, at least zero. It halts an upward drift, at a
plateau that grows with its period, and it cannot reverse a downward drift, because the margin that would
needs to be negative and the margin has a floor of zero.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import lognormal_q
from hpa_vpa import simulate


def run(sigma, period, days=60):
    s, _ = simulate(0.5, days=days, noise_sigma=sigma, request_floor=1e-6, supervisor_h=period, sample_h=24)
    return [x[1] for x in s]


class Supervisor(unittest.TestCase):

    def test_it_halts_the_upward_drift(self):
        r = run(0.0, 1)
        self.assertEqual(r[-1], r[-30])
        self.assertLess(r[-1], 2 * r[0])

    def test_the_plateau_grows_with_the_period(self):
        plateaus = [run(0.0, t)[-1] for t in (1, 24, 96)]
        self.assertLess(plateaus[0], plateaus[1])
        self.assertLess(plateaus[1], plateaus[2])

    def test_it_saturates_in_the_downward_regime(self):
        self.assertLess(1.0 / (0.5 * lognormal_q(1.2)) - 1.0, 0.0)
        r = run(1.2, 1)
        self.assertLess(r[-1], r[0])


if __name__ == '__main__':
    unittest.main()
