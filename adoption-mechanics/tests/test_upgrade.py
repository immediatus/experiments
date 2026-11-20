"""Checks the upgrade condition: a panel improves from (p0, rho0) to (p1, rho1) exactly when its large-panel
error floor falls, and the log-form margin has the same sign.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest
from statistics import NormalDist

from sensors import error_floor
from upgrade import critical_elasticity, upgrade_improves, upgrade_margin


class Upgrade(unittest.TestCase):

    def test_better_members_worse_panel(self):
        self.assertFalse(upgrade_improves(0.30, 0.10, 0.20, 0.35))   # floor 4.9% -> 7.7%

    def test_condition_agrees_with_floor(self):
        for p0, r0, p1, r1 in [(0.30, 0.10, 0.20, 0.35), (0.20, 0.35, 0.10, 0.40), (0.25, 0.2, 0.25, 0.1),
                               (0.15, 0.50, 0.10, 0.65)]:
            better = error_floor(p1, r1) < error_floor(p0, r0)
            self.assertEqual(upgrade_improves(p0, r0, p1, r1), better)
            self.assertEqual(upgrade_margin(p0, r0, p1, r1) > 0, better)


class CriticalElasticity(unittest.TestCase):

    def test_falls_as_members_improve(self):
        self.assertGreater(critical_elasticity(0.3), critical_elasticity(0.2))
        self.assertGreater(critical_elasticity(0.2), critical_elasticity(0.05))

    def test_small_error_limit(self):
        z = NormalDist().inv_cdf(0.001)
        self.assertAlmostEqual(critical_elasticity(0.001), 2.0 / (z * z), delta=0.05)

    def test_matches_margin_sign_for_small_steps(self):
        p0, r0 = 0.2, 0.4
        e = critical_elasticity(p0)
        p1 = p0 * 0.999
        for k, sign in ((0.9, 1), (1.1, -1)):
            r1 = r0 * (p1 / p0) ** (-k * e)
            self.assertEqual(upgrade_margin(p0, r0, p1, r1) > 0, sign > 0)


if __name__ == '__main__':
    unittest.main()
