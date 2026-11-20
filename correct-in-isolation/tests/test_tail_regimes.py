"""Checks Part 1's gap: the vertical loop sizes from a percentile of per-pod samples, the horizontal loop
holds the mean across pods. With per-pod usage multiplied by a lognormal factor of mean one and shape
sigma, the percentile-to-mean ratio is q(sigma) = exp(z_p sigma - sigma^2 / 2), which rises and then falls,
so the pair's regime over tail weight is reentrant: drift up, rest, drift down, rest, drift up.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import lognormal_q, pareto_q, regime, regime_boundaries
from hpa_vpa import simulate


class ClosedForm(unittest.TestCase):

    def test_q_at_zero_tail_is_one(self):
        self.assertAlmostEqual(lognormal_q(0.0), 1.0)

    def test_q_peaks_at_the_quantile(self):
        z = 1.2815515655446004
        self.assertAlmostEqual(lognormal_q(z), math.exp(z * z / 2), places=9)
        self.assertGreater(lognormal_q(z), lognormal_q(z - 0.1))
        self.assertGreater(lognormal_q(z), lognormal_q(z + 0.1))

    def test_pareto_q(self):
        self.assertAlmostEqual(pareto_q(2.0), 10 ** 0.5 / 2, places=12)

    def test_reentrant_regimes_at_half(self):
        self.assertEqual(regime(0.5, lognormal_q(0.2)), 'drift up')
        self.assertEqual(regime(0.5, lognormal_q(0.55)), 'rest')
        self.assertEqual(regime(0.5, lognormal_q(1.2)), 'drift down')
        self.assertEqual(regime(0.5, lognormal_q(2.0)), 'rest')
        self.assertEqual(regime(0.5, lognormal_q(2.4)), 'drift up')

    def test_boundaries(self):
        b = regime_boundaries(0.5)
        self.assertEqual(len(b), 4)
        for x, y in zip(b, (0.4294, 0.7116, 1.8515, 2.1337)):
            self.assertAlmostEqual(x, y, places=4)


class Simulated(unittest.TestCase):

    def growth(self, sigma):
        samples, _ = simulate(0.5, days=30, noise_sigma=sigma, request_floor=1e-6)
        return samples[-1][1] / samples[0][1]

    def test_simulation_follows_the_regimes(self):
        self.assertGreater(self.growth(0.0), 4.0)
        self.assertLess(abs(math.log(self.growth(0.55))), math.log(1.5))
        self.assertLess(self.growth(1.2), 0.67)


if __name__ == '__main__':
    unittest.main()
