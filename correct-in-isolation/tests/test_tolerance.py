"""Per-direction horizontal tolerance (HPAConfigurableTolerance, GA in Kubernetes 1.37): a
scale-up tolerance wide enough to swallow the vertical loop's step stops the staircase, and the
width it needs is the step factor minus one."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'model'))

from formulas import directional_band, equilibrium_band, step_factor, stopping_scale_up_tolerance
from hpa_vpa import simulate


class DirectionalTolerance(unittest.TestCase):
    def test_symmetric_case_is_the_old_band(self):
        for q in (1.0, 1.2):
            self.assertEqual(directional_band(q=q, tol_up=0.1, tol_down=0.1), equilibrium_band(q=q))

    def test_scale_up_tolerance_moves_only_the_low_edge(self):
        lo, hi = directional_band(tol_up=0.5, tol_down=0.1)
        self.assertAlmostEqual(hi, equilibrium_band()[1], places=12)
        self.assertAlmostEqual(lo, 1 / 1.15 / 1.5, places=12)

    def test_stopping_tolerance_is_step_factor_minus_one(self):
        self.assertAlmostEqual(stopping_scale_up_tolerance(0.5), step_factor(0.5) - 1, places=12)
        self.assertAlmostEqual(stopping_scale_up_tolerance(0.5), 0.7391304347826086, places=12)
        self.assertEqual(stopping_scale_up_tolerance(0.9), 0.0)

    def test_target_at_the_low_edge_rests(self):
        u_h = 0.5
        tol = stopping_scale_up_tolerance(u_h)
        self.assertAlmostEqual(directional_band(tol_up=tol, tol_down=0.1)[0], u_h, places=12)

    def test_simulated_staircase_stops_above_and_runs_below(self):
        stopped = simulate(0.5, days=30, tol_up=0.75)
        self.assertIsNone(stopped[1])
        self.assertLess(stopped[0][-1][1] / stopped[0][0][1], 1.5)
        running = simulate(0.5, days=30, tol_up=0.60)
        self.assertGreater(running[0][-1][1] / running[0][0][1], 4.0)

    def test_simulated_threshold_lies_inside_the_bucket_bracket(self):
        # the histogram's 5% buckets shrink the step by up to that much, so the simulated
        # threshold lies between (step factor / 1.05) - 1 and the bucket-free step factor - 1
        lo, hi = step_factor(0.5, bucket=1.05) - 1, stopping_scale_up_tolerance(0.5)
        self.assertIsNotNone(simulate(0.5, days=40, tol_up=lo - 0.005)[1])
        self.assertLess(simulate(0.5, days=40, tol_up=hi)[0][-1][1], 11)


if __name__ == '__main__':
    unittest.main()
