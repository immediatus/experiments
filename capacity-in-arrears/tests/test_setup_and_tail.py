"""Checks the request-level setup simulator of setup_sim against the closed forms of Gandhi, Harchol-Balter and
Adan (2010) it is compared with, and the Monte Carlo helpers of tail_study: the quantile, the Hill estimator on
a sample of known tail, and the shape of a study's output.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import random
import unittest

from setup_sim import erlang_c_mean_response, onoff_inf_mean_response, simulate
from tail_study import q, study, tail_index


class SetupFarm(unittest.TestCase):

    def test_erlang_c_with_one_server_is_m_m_1(self):
        self.assertAlmostEqual(erlang_c_mean_response(0.7, 1.0, 1), 1.0 / (1.0 - 0.7), places=12)

    def test_staggered_setup_matches_theorem_1(self):
        exact = 1.0 / 0.5 + erlang_c_mean_response(0.7, 1.0, 4)
        self.assertAlmostEqual(simulate(0.7, 1.0, 0.5, 4, True, 1, jobs=40000, warm=4000), exact, delta=0.05 * exact)

    def test_unbounded_setup_matches_theorem_2(self):
        exact = onoff_inf_mean_response(0.7, 1.0, 0.5)
        self.assertAlmostEqual(simulate(0.7, 1.0, 0.5, None, False, 1, jobs=40000, warm=4000), exact,
                               delta=0.03 * exact)

    def test_deterministic_for_a_seed(self):
        self.assertEqual(simulate(0.7, 1.0, 0.5, 4, True, 2, jobs=5000, warm=500),
                         simulate(0.7, 1.0, 0.5, 4, True, 2, jobs=5000, warm=500))


class TailStudy(unittest.TestCase):

    def test_quantile_takes_the_floor_index(self):
        v = list(range(10, 0, -1))
        self.assertEqual(q(v, 0.5), 6)
        self.assertEqual(q(v, 1.0), 10)

    def test_hill_estimator_recovers_a_pareto_exponent(self):
        rng = random.Random(5)
        sample = [(1.0 - rng.random()) ** (-1.0 / 2.0) for _ in range(20000)]
        self.assertAlmostEqual(tail_index(sample), 2.0, delta=0.15)

    def test_study_returns_one_entry_per_trial(self):
        ks, tc, bl, ov, lost = study(1.5, 12)
        self.assertEqual({len(x) for x in (ks, tc, bl, ov, lost)}, {12})
        self.assertTrue(all(1.5 <= k <= 2000.0 for k in ks))
        self.assertTrue(all(0 <= t <= 3600 for t in tc))


if __name__ == '__main__':
    unittest.main()
