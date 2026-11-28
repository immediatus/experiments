"""Checks Part 6's cross-seam reading of Part 1's two fixes: a target moved to the vertical loop's
resting utilization and a scale-up tolerance that reaches it both stop the drift, but on Part 2's
nested surge the tolerance keeps the 50% target's growth per round and costs about one round, while
the moved target slows the surge several times over.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import stopping_scale_up_tolerance, vpa_utilisation
from nested import simulate


class ToleranceSurge(unittest.TestCase):
    """The two fixes rest at the same utilization; tolerance fix costs about a round; moved target is several times
    slower."""

    def test_the_two_fixes_rest_at_the_same_utilization(self):
        self.assertAlmostEqual(0.5 * (1 + stopping_scale_up_tolerance(0.5)), vpa_utilisation(), places=12)

    def test_tolerance_fix_costs_about_a_round(self):
        tol = round(stopping_scale_up_tolerance(0.5), 2)
        k = 30 * vpa_utilisation() / 0.5          # thirtyfold of the demand the fixed pair rests at
        base = simulate(30)
        fixed = simulate(k, tol=tol)
        self.assertGreaterEqual(fixed, base)
        self.assertLessEqual(fixed, base + 90 + 210)

    def test_moved_target_is_several_times_slower(self):
        tol = round(stopping_scale_up_tolerance(0.5), 2)
        k = 30 * vpa_utilisation() / 0.5
        self.assertGreater(simulate(30, target=round(vpa_utilisation(), 2)), 4 * simulate(k, tol=tol))


if __name__ == '__main__':
    unittest.main()
