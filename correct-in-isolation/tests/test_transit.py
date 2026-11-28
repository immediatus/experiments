"""Checks the signal seam in transit: the paired loops drifting at a 50% target, then a fix applied while the
replica count is mid-staircase. Moving the target to 0.8 lowers the replica count at once and ends the drift;
a scale-up tolerance of 0.739 ends the drift without a jump. Every fix is applied at one hour of a run that
otherwise matches the steady run before it.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from hpa_vpa import simulate


class Transit(unittest.TestCase):
    """No change matches the plain run; target move ends the drift; tolerance ends the drift."""

    def test_no_change_matches_the_plain_run(self):
        plain = simulate(0.5, days=20, return_jumps=True)[2]
        same = simulate(0.5, days=20, return_jumps=True, change=(10000.0, {}))[2]
        self.assertEqual(plain, same)

    def test_target_move_ends_the_drift(self):
        _, _, jumps = simulate(0.5, days=40, return_jumps=True, change=(300.0, {'target': 0.8}))
        after = [j for j in jumps if j[0] > 300.0 + 1.0]
        self.assertTrue(all(j[0] < 600.0 for j in after))

    def test_tolerance_ends_the_drift(self):
        _, _, jumps = simulate(0.5, days=40, return_jumps=True, change=(300.0, {'tol_up': 0.739}))
        self.assertFalse([j for j in jumps if j[0] > 400.0])


if __name__ == '__main__':
    unittest.main()
