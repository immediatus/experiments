"""Checks Part 1's model against properties it must have whatever its inputs: the relative gain
array's rows and columns sum to one, a shared metric makes the gain matrix singular, the
recommended split pairing has relative gain one without coupling, both loops leave total
requested capacity at demand / target, and the closed forms agree with the simulation.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import random
import unittest

from formulas import (
    coupled_relative_gain,
    custom_metric_relative_gain,
    doubling_bracket,
    equilibrium_band,
    relative_gain_array,
    resting_margin,
    same_metric_gain,
    split_metric_gain,
    step_factor,
    step_interval,
    vpa_utilisation,
)
from hpa_vpa import simulate


class RelativeGainArray(unittest.TestCase):
    """Rows and columns sum to one; shared metric is singular; split pairing without coupling is one; custom metric
    gain does not depend on the metric elasticity; resting margin is the band seen from the vertical side; vertical
    tolerance widens the band by its own factor; coupling closed form."""

    def test_rows_and_columns_sum_to_one(self):
        rng = random.Random(1)
        for _ in range(200):
            g = [[rng.uniform(-3, 3) for _ in range(2)] for _ in range(2)]
            rga = relative_gain_array(g)
            if rga is None:
                continue
            for i in range(2):
                self.assertAlmostEqual(sum(rga[i]), 1.0, places=9)
                self.assertAlmostEqual(rga[0][i] + rga[1][i], 1.0, places=9)

    def test_shared_metric_is_singular(self):
        self.assertIsNone(relative_gain_array(same_metric_gain()))

    def test_split_pairing_without_coupling_is_one(self):
        for theta in (0.0, 0.5, 1.0):
            self.assertEqual(relative_gain_array(split_metric_gain(0.0, theta))[0][0], 1.0)

    def test_custom_metric_gain_does_not_depend_on_the_metric_elasticity(self):
        for gamma in (0.0, 0.25, 0.5, 0.9):
            for epsilon in (0.3, 1.0, 4.0):
                self.assertAlmostEqual(custom_metric_relative_gain(gamma, epsilon), 1 / (1 - gamma), places=12)
        self.assertIsNone(custom_metric_relative_gain(1.0, 2.0))
        self.assertEqual(custom_metric_relative_gain(0.0), 1.0)

    def test_resting_margin_is_the_band_seen_from_the_vertical_side(self):
        for u_h in (0.5, 0.6, 0.7, 0.8, 0.9):
            for q in (1.0, 1.2, 1.5):
                lo, hi = resting_margin(u_h, q)
                for m in (lo, hi):
                    band = equilibrium_band(m, q)
                    self.assertTrue(band[0] - 1e-12 <= u_h <= band[1] + 1e-12)
                self.assertAlmostEqual((1 + lo) * q, 1 / (u_h * 1.1), places=12)
                self.assertAlmostEqual((1 + hi) * q, 1 / (u_h * 0.9), places=12)

    def test_vertical_tolerance_widens_the_band_by_its_own_factor(self):
        for q in (1.0, 1.2, 1.5):
            lo0, hi0 = equilibrium_band(q=q)
            lo1, hi1 = equilibrium_band(q=q, vtol=0.1)
            self.assertAlmostEqual(lo1, lo0 / 1.1, places=12)
            self.assertAlmostEqual(hi1, hi0 / 0.9, places=12)
            for u_h in (0.5, 0.7):
                m = resting_margin(u_h, q, vtol=0.1)
                self.assertAlmostEqual(equilibrium_band(m[0], q, vtol=0.1)[0], u_h, places=12)

    def test_coupling_closed_form(self):
        for beta, theta in ((0.5, 1.0), (2.0, 1.0), (0.3, 0.5)):
            self.assertAlmostEqual(coupled_relative_gain(beta, theta), 1 / (1 - beta * theta), places=12)
        self.assertIsNone(coupled_relative_gain(1.0, 1.0))


class DocumentedUpdates(unittest.TestCase):
    """The drift under the vertical autoscaler's documented update rule: admission at the
    recommendation, updates outside the bounds, or after 12 h beyond a 10% difference."""

    def test_closed_bounds_reproduce_instant_application(self):
        for target in (0.5, 0.6):
            a = simulate(target, days=200)[1]
            b = simulate(target, days=200, updates='documented', bound=0.0)[1]
            self.assertLess(abs(b / a - 1.0), 0.01)

    def test_the_widest_deadband_does_not_stop_the_drift_below_the_band(self):
        for target in (0.5, 0.6):
            self.assertIsNotNone(simulate(target, days=200, updates='documented', bound=None)[1])


class TwoLoopsOneMetric(unittest.TestCase):
    """Requested capacity is held by the horizontal loop; inside the band nothing drifts; the staircase steps every
    interval; below the band doubling lies in the bracket; doubling does not depend on demand or start; a daily
    cycle does not stop the drift; the law holds at other recommender settings; above the band replicas fall."""

    def test_requested_capacity_is_held_by_the_horizontal_loop(self):
        """Below the band, replicas and requests drift, but utilisation never leaves the horizontal
        loop's tolerance by more than the rounding of one replica."""
        samples, _ = simulate(0.5, days=30, sample_h=6)
        for _, n, _, u, _ in samples:
            self.assertLessEqual(abs(u / 0.5 - 1.0), 0.1 + 1.0 / n + 1e-9)

    def test_inside_the_band_nothing_drifts(self):
        lo, hi = equilibrium_band()
        for target in (lo * 1.01, vpa_utilisation(), hi * 0.99):
            samples, doubling = simulate(target, days=60)
            self.assertIsNone(doubling)
            self.assertIsNone(doubling_bracket(target))

    def test_the_staircase_steps_every_interval(self):
        self.assertAlmostEqual(step_interval(), 24 * 3.321928, places=3)
        self.assertAlmostEqual(step_factor(0.5), 1 / 0.575, places=12)

    def test_below_the_band_doubling_lies_in_the_bracket(self):
        for target in (0.4, 0.5, 0.6, 0.7, 0.75):
            lo, hi = doubling_bracket(target)
            _, doubling = simulate(target, days=400)
            self.assertIsNotNone(doubling)
            self.assertGreaterEqual(doubling, lo * 0.99)
            self.assertLessEqual(doubling, hi * 1.01)

    def test_doubling_does_not_depend_on_demand_or_start(self):
        """The drift is scale-free: demand and the starting replica count do not change its
        long-run rate, up to the rounding of one replica."""
        base = simulate(0.5, days=80)[1]
        for demand, replicas in ((10.0, 10), (1000.0, 40), (100.0, 100)):
            self.assertLess(abs(simulate(0.5, demand=demand, replicas=replicas, days=80)[1] / base - 1.0), 0.03)

    def test_a_daily_cycle_does_not_stop_the_drift(self):
        """The staircase law is for steady demand; a daily cycle changes the rate, here faster, but
        the drift continues."""
        base = simulate(0.5, days=120)[1]
        for amplitude in (0.3, 0.6):
            doubling = simulate(0.5, amplitude=amplitude, days=120)[1]
            self.assertIsNotNone(doubling)
            self.assertLess(doubling, base)

    def test_the_law_holds_at_other_recommender_settings(self):
        for kw in (dict(percentile=0.5), dict(percentile=0.95), dict(half_life=12.0), dict(margin=0.3)):
            h, p = kw.get('half_life', 24.0), kw.get('percentile', 0.9)
            lo, hi = doubling_bracket(0.5, margin=kw.get('margin', 0.15), half_life=h, percentile=p)
            _, doubling = simulate(0.5, days=300, request_floor=0.001, warmup_h=2.5 * step_interval(h, p), **kw)
            self.assertIsNotNone(doubling)
            self.assertGreaterEqual(doubling, lo * 0.99)
            self.assertLessEqual(doubling, hi * 1.01)

    def test_above_the_band_replicas_fall(self):
        samples, _ = simulate(0.9, margin=0.6, days=30)
        self.assertLess(samples[-1][1], samples[0][1])


if __name__ == '__main__':
    unittest.main()
