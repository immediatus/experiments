"""Checks Part 4's binding over time: a webhook that must be up to admit its own replacements binds
when every replica is down at once; with one replica that is its first node failure, and with Z the
mean time is close to 1 / (Z lam (lam w)^(Z - 1)) when lam w is small, checked against an event
simulation at accelerated rates.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import cycle_mean_time_to_bind
from recovery import simulated_time_to_bind


class TimeToBind(unittest.TestCase):
    """One replica binds at its first failure; closed form against simulation."""

    def test_one_replica_binds_at_its_first_failure(self):
        self.assertEqual(cycle_mean_time_to_bind(1, 30.0, 0.01), 30.0)
        self.assertAlmostEqual(simulated_time_to_bind(1, 30.0, 0.01, runs=4000), 30.0, delta=1.5)

    def test_closed_form_against_simulation(self):
        # The closed form is the leading term: its relative error is of order Z lam w, plus sampling error
        # of about one over the square root of the runs, since the time to bind is close to exponential.
        runs = 4000
        for z, w in ((2, 1.0), (2, 0.3), (3, 1.0), (3, 2.0)):
            closed = cycle_mean_time_to_bind(z, 30.0, w)
            sim = simulated_time_to_bind(z, 30.0, w, runs=runs)
            tol = 2 * z * w / 30.0 + 4 / runs ** 0.5
            self.assertLess(abs(sim - closed) / closed, tol, msg='%d %g %g %g' % (z, w, closed, sim))
            self.assertGreater(sim, closed * 0.97)


if __name__ == '__main__':
    unittest.main()
