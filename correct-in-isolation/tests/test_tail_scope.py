"""Checks the scope of Part 1's tail regimes. Per-pod samples are the mean times a lognormal factor of mean one
and shape sigma. The horizontal loop reads the mean of n pods' samples, whose coefficient of variation is
sqrt((exp(sigma^2) - 1) / n), so the many-pod limit the regimes assume needs n large against exp(sigma^2) - 1.
The share of the mean carried by samples above c times the mean is 1 - Phi((ln c - sigma^2/2) / sigma), the
size-biased tail: a node with c times a pod's mean usage in cores cannot serve that share.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import random
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import pod_mean_cv, spike_share


class TailScope(unittest.TestCase):

    def test_cv_closed_form(self):
        self.assertAlmostEqual(pod_mean_cv(2.4, 10), math.sqrt((math.exp(5.76) - 1) / 10))
        self.assertEqual(pod_mean_cv(0.0, 10), 0.0)

    def test_cv_by_sampling(self):
        rng = random.Random(4)
        sigma, n = 0.55, 10
        means = [sum(math.exp(sigma * rng.gauss(0, 1) - sigma ** 2 / 2) for _ in range(n)) / n for _ in range(40000)]
        m = sum(means) / len(means)
        sd = math.sqrt(sum((x - m) ** 2 for x in means) / len(means))
        self.assertAlmostEqual(sd / m, pod_mean_cv(sigma, n), delta=0.01)

    def test_spike_share_by_sampling(self):
        rng = random.Random(5)
        sigma, c = 1.2, 8.0
        xs = [math.exp(sigma * rng.gauss(0, 1) - sigma ** 2 / 2) for _ in range(400000)]
        self.assertAlmostEqual(sum(x for x in xs if x > c) / sum(xs), spike_share(sigma, c), delta=0.01)

    def test_spike_share_limits(self):
        self.assertLess(spike_share(0.3, 8.0), 1e-6)
        self.assertGreater(spike_share(2.4, 8.0), 0.6)


if __name__ == '__main__':
    unittest.main()
