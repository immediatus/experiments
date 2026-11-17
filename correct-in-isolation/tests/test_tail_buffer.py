"""Checks Part 2's buffer controller. After every surge it reads the surge's size, estimates the tail
exponent by maximum likelihood, and sets the covered rounds that minimize the mean cost for that
exponent, up to the buffer's limit. A replica count capped at maxReplicas censors the reading; read
naively the cap makes the tail look lighter, alpha / (1 - (kmin / cap)^alpha), which can carry an
exponent below 1 across it.

Run: python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import censored_naive, censoring_crossing, cover_cost, optimal_cover, pareto_mle
from tail_buffer import run


def grid(alpha, n=20000, kmin=2.0):
    return [kmin * (1.0 - (i + 0.5) / n) ** (-1.0 / alpha) for i in range(n)]


class Censoring(unittest.TestCase):

    def test_closed_form_matches_the_grid(self):
        for alpha in (0.69, 1.1, 1.5):
            naive = pareto_mle([min(k, 20.0) for k in grid(alpha)], 2.0)
            self.assertAlmostEqual(naive, censored_naive(alpha, 2.0, 20.0), places=3)

    def test_cap_carries_a_heavy_tail_across_one(self):
        self.assertGreater(censored_naive(0.9, 2.0, 20.0), 1.0)
        self.assertGreater(censored_naive(0.69, 2.0, 10.0), 1.0)
        self.assertLess(censored_naive(0.69, 2.0, 20.0), 1.0)


    def test_crossing_is_where_the_naive_estimate_reads_one(self):
        for cap in (10.0, 20.0, 50.0):
            a = censoring_crossing(2.0, cap)
            self.assertAlmostEqual(censored_naive(a, 2.0, cap), 1.0, places=9)
            self.assertLess(censored_naive(a - 0.01, 2.0, cap), 1.0)


class Controller(unittest.TestCase):

    def test_oracle_holds_the_optimal_cover(self):
        out = run(1.5, rule='oracle', surges=50)
        self.assertEqual(out['final_c'], optimal_cover(1.5, 100, 3600, 210)[1])

    def test_estimate_converges_to_the_oracle_cover(self):
        for alpha in (1.5, 2.0, 3.0):
            out = run(alpha, rule='mle', surges=1000)
            self.assertEqual(out['final_c'], optimal_cover(alpha, 100, 3600, 210)[1])

    def test_heavy_tail_pins_the_buffer_at_its_limit(self):
        out = run(0.9, rule='mle', surges=1000, cap=20.0, max_c=6)
        self.assertEqual(out['final_c'], 6)

    def test_naive_reading_of_a_capped_count_crosses_one(self):
        for seed in range(1, 6):
            self.assertGreater(run(0.8, rule='mle', surges=1000, seed=seed, cap=10.0, fix=False)['alpha_hat'], 1.0)
            self.assertLess(run(0.8, rule='mle', surges=1000, seed=seed, cap=10.0)['alpha_hat'], 1.0)

    def test_expected_cost_is_the_mean_cover_cost(self):
        out = run(1.5, rule='oracle', surges=20)
        c = optimal_cover(1.5, 100, 3600, 210)[1]
        self.assertAlmostEqual(out['expected_cost'], cover_cost(c, 1.5, 16, 100, 3600, 90, 210))

    def test_estimate_close_to_oracle_in_expectation(self):
        oracle = run(1.5, rule='oracle', surges=1000)['expected_cost']
        self.assertLess(run(1.5, rule='mle', surges=1000)['expected_cost'] / oracle, 1.05)
        self.assertGreater(run(1.5, rule='peak', surges=1000)['expected_cost'] / oracle, 1.5)

    def test_peak_rule_only_ratchets_up(self):
        out = run(1.5, rule='peak', surges=500)
        self.assertEqual(out['covers'], sorted(out['covers']))

    def test_same_seed_same_surges(self):
        self.assertEqual(run(1.5, rule='mle', surges=100)['sizes'], run(1.5, rule='peak', surges=100)['sizes'])


if __name__ == '__main__':
    unittest.main()
