"""Checks Part 2's tail results. Surge sizes Pareto with exponent alpha above the surge that just saturates
the running pods, so the pods it needs, N* = k n0 u / l, are Pareto above n0. Rounds then have a geometric
tail and a finite mean for every alpha, while the pod-seconds short during the ramp have the surge's own
tail: finite mean only above alpha = 1. Nesting multiplies the node-wait part of the shortfall by
1 / (1 - g^(1 - alpha)), and each covered round divides it by g^(alpha - 1).

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import (cover_cost, nesting_multiplier, optimal_cover, pareto_mean_time, pareto_mle,
                      pareto_rounds_tail, pareto_shortfall, ramp_shortfall)
from nested import simulate


def grid(alpha, n=20000, kmin=2.0):
    return [kmin * (1.0 - (i + 0.5) / n) ** (-1.0 / alpha) for i in range(n)]


class Ramp(unittest.TestCase):

    def test_thirtyfold_ladder(self):
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 210), 216000.0)
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 0), 64800.0)
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 210, separated=True), 111840.0)

    def test_covered_rounds_pay_pod_time_only(self):
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 210, c=4), ramp_shortfall(30, 16, 90, 0))
        self.assertAlmostEqual(ramp_shortfall(30, 16, 90, 210, c=1), 216000.0 - 224 * 210)

    def test_simulation_matches_within_latency(self):
        for k in (5, 10, 30):
            short = []
            simulate(k, shortfall=short)
            closed = ramp_shortfall(k, 16, 90, 210)
            self.assertLess(abs(short[0] - closed) / closed, 0.12)


class Tail(unittest.TestCase):

    def test_rounds_tail_is_geometric(self):
        self.assertEqual(pareto_rounds_tail(1, 1.5), 1.0)
        self.assertAlmostEqual(pareto_rounds_tail(3, 1.5), 2 ** (-3.0))
        ks = grid(1.5)
        share = sum(1 for k in ks if ramp_rounds(k) >= 3) / len(ks)
        self.assertAlmostEqual(share, 2 ** (-3.0), places=3)

    def test_mean_time_finite_for_every_alpha(self):
        self.assertAlmostEqual(pareto_mean_time(1.0, 90, 210), 600.0)
        self.assertTrue(math.isfinite(pareto_mean_time(0.5, 90, 210)))

    def test_shortfall_diverges_at_one(self):
        self.assertEqual(pareto_shortfall(1.0, 16, 90, 210), math.inf)
        self.assertEqual(pareto_shortfall(0.69, 16, 90, 210), math.inf)
        self.assertAlmostEqual(pareto_shortfall(2.0, 16, 90, 210), 9600.0)

    def test_closed_form_against_quantile_grid(self):
        for alpha in (2.5, 3.0):
            ks = grid(alpha)
            for c in (0, 2):
                mean = math.fsum(ramp_shortfall(k, 16, 90, 210, c=c) for k in ks) / len(ks)
                self.assertLess(abs(mean / pareto_shortfall(alpha, 16, 90, 210, c=c) - 1), 0.02)
            mean = math.fsum(ramp_shortfall(k, 16, 90, 210, separated=True) for k in ks) / len(ks)
            self.assertLess(abs(mean / pareto_shortfall(alpha, 16, 90, 210, separated=True) - 1), 0.02)

    def test_nesting_multiplier(self):
        for alpha in (1.5, 2.0, 3.0):
            nested = pareto_shortfall(alpha, 16, 90, 210) - pareto_shortfall(alpha, 16, 90, 0)
            separated = pareto_shortfall(alpha, 16, 90, 210, separated=True) - pareto_shortfall(alpha, 16, 90, 0)
            self.assertAlmostEqual(nested / separated, nesting_multiplier(alpha))
        self.assertAlmostEqual(nesting_multiplier(2.0), 2.0)

    def test_each_round_divides_the_node_part(self):
        alpha = 1.5
        def part(c):
            return pareto_shortfall(alpha, 16, 90, 210, c=c) - pareto_shortfall(alpha, 16, 90, 0)
        self.assertAlmostEqual(part(3) / part(2), 2 ** (1 - alpha))


class Cover(unittest.TestCase):

    def test_integer_optimum(self):
        for alpha in (1.2, 1.5, 2.0, 3.0):
            best = min(range(25), key=lambda c: cover_cost(c, alpha, 16, 100, 3600, 90, 210))
            self.assertEqual(optimal_cover(alpha, 100, 3600, 210)[1], best)

    def test_cover_falls_as_the_tail_lightens(self):
        xs = [optimal_cover(a, 100, 3600, 210)[0] for a in (1.1, 1.5, 2.0, 3.0)]
        self.assertEqual(xs, sorted(xs, reverse=True))

    def test_cover_never_below_no_headroom(self):
        x, c = optimal_cover(3.0, 10, 3600, 210)
        self.assertEqual(x, 1.0)
        self.assertEqual(c, 0)

    def test_no_finite_cover_at_or_below_one(self):
        self.assertEqual(optimal_cover(1.0, 100, 3600, 210)[0], math.inf)


class Estimate(unittest.TestCase):

    def test_mle_recovers_alpha(self):
        self.assertAlmostEqual(pareto_mle(grid(1.5), 2.0), 1.5, places=2)

    def test_censoring_biases_up_and_the_fix_removes_it(self):
        ks = grid(1.5)
        naive = pareto_mle([min(k, 20.0) for k in ks], 2.0)
        fixed = pareto_mle([min(k, 20.0) for k in ks], 2.0, cap=20.0)
        self.assertGreater(naive, 1.54)
        self.assertAlmostEqual(fixed, 1.5, places=2)


def ramp_rounds(k):
    return max(0, math.ceil(math.log2(k / 2.0) - 1e-9))


if __name__ == '__main__':
    unittest.main()
