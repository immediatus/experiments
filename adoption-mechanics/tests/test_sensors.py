"""Checks the sensors stage: the majority-vote error floor of a large correlated panel against simulation,
its limits at rho 0 and 1, the tie rule for even panels, the exact majority error of a finite panel by integration over
the shared factor, and the effective number of independent opinions.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import math
import random
import unittest
from statistics import NormalDist

from sensors import effective_n, error_floor, exact_majority_error, indicator_correlation, latent_votes, majority_error, variance_floor


class LatentVotes(unittest.TestCase):

    def test_certain_error_and_certain_success(self):
        rng = random.Random(1)
        self.assertEqual(latent_votes(5, 1.0, 0.3, rng), [True] * 5)
        self.assertEqual(latent_votes(5, 0.0, 0.3, rng), [False] * 5)

    def test_given_shared_factor_is_not_drawn(self):
        a, b = random.Random(9), random.Random(9)
        given = latent_votes(200, 0.3, 0.5, a, shared=-1.0)
        tau = NormalDist().inv_cdf(0.3)
        expected = [math.sqrt(0.5) * -1.0 + math.sqrt(0.5) * b.gauss(0.0, 1.0) < tau for _ in range(200)]
        self.assertEqual(given, expected)


class Floor(unittest.TestCase):

    def test_floor_matches_simulation(self):
        for p, rho in [(0.30, 0.10), (0.15, 0.60), (0.10, 0.60)]:
            sim = majority_error(201, p, rho, trials=20000, seed=7)
            self.assertAlmostEqual(sim, error_floor(p, rho), delta=0.012)

    def test_edges(self):
        self.assertEqual(error_floor(0.2, 0.0), 0.0)
        self.assertAlmostEqual(error_floor(0.2, 1.0), 0.2)

    def test_even_panel_ties_count_as_errors(self):
        # two independent members who each err half the time: the panel errs unless both are right
        self.assertAlmostEqual(majority_error(2, 0.5, 0.0, trials=40000, seed=3), 0.75, delta=0.01)


class ExactMajority(unittest.TestCase):

    def test_independent_panel_is_the_binomial_tail(self):
        for n in (15, 4):
            tail = math.fsum(math.comb(n, j) * 0.3 ** j * 0.7 ** (n - j) for j in range((n + 1) // 2, n + 1))
            self.assertAlmostEqual(exact_majority_error(n, 0.3, 0.0), tail, places=12)

    def test_even_panel_ties_count_as_errors(self):
        self.assertGreater(exact_majority_error(4, 0.3, 0.25), exact_majority_error(5, 0.3, 0.25))

    def test_matches_simulation(self):
        exact, sim = exact_majority_error(15, 0.3, 0.25), majority_error(15, 0.3, 0.25, 40000, 3)
        self.assertLess(abs(exact - sim), 4 * math.sqrt(exact * (1 - exact) / 40000))

    def test_approaches_the_floor(self):
        self.assertAlmostEqual(exact_majority_error(201, 0.3, 0.25), error_floor(0.3, 0.25), delta=0.006)

    def test_edges(self):
        self.assertEqual(exact_majority_error(15, 0.0, 0.25), 0.0)
        self.assertEqual(exact_majority_error(15, 1.0, 0.25), 1.0)
        self.assertAlmostEqual(exact_majority_error(15, 0.3, 1.0), 0.3, places=12)


class EffectiveSize(unittest.TestCase):

    def test_effective_n_limit(self):
        self.assertAlmostEqual(effective_n(10 ** 6, 0.25), 4.0, places=3)

    def test_effective_n_one_member(self):
        self.assertEqual(effective_n(1, 0.6), 1.0)

    def test_variance_floor(self):
        self.assertAlmostEqual(variance_floor(2.0, 0.3), 0.6)


class IndicatorCorrelation(unittest.TestCase):

    def test_limits(self):
        self.assertAlmostEqual(indicator_correlation(0.3, 0.0), 0.0, places=6)
        self.assertAlmostEqual(indicator_correlation(0.3, 1.0), 1.0, places=6)

    def test_below_latent(self):
        self.assertLess(indicator_correlation(0.3, 0.25), 0.25)
        self.assertGreater(indicator_correlation(0.3, 0.25), 0.1)

    def test_matches_simulated_votes(self):
        rng = random.Random(4)
        a = b = ab = 0
        trials = 40000
        for _ in range(trials):
            x, y = latent_votes(2, 0.3, 0.25, rng)
            a += x
            b += y
            ab += x and y
        pa, pb, pab = a / trials, b / trials, ab / trials
        phi = (pab - pa * pb) / ((pa * (1 - pa) * pb * (1 - pb)) ** 0.5)
        self.assertAlmostEqual(phi, indicator_correlation(0.3, 0.25), delta=0.015)


if __name__ == '__main__':
    unittest.main()
