"""Checks Part 3's bookmarks: without them a re-watch resumes from the last event its selector saw, so
when every watch lasts at least the history it is answered 410 exactly when no event came in the last
T_h seconds, with probability exp(-lam T_h); the list load this adds with no trigger at all is the
forced backlog times that probability over the mean watch period.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import no_bookmark_gone_probability, no_bookmark_load
from relist import simulated_no_bookmark_gone


class Bookmarks(unittest.TestCase):
    """Probability against simulation; load."""

    def test_probability_against_simulation(self):
        for per_hour in (0.0, 6.0, 18.0, 60.0):
            closed = no_bookmark_gone_probability(per_hour / 3600.0, 300.0)
            sim = simulated_no_bookmark_gone(per_hour / 3600.0, 300.0, watches=20000)
            self.assertAlmostEqual(sim, closed, delta=0.012, msg=str(per_hour))

    def test_load(self):
        self.assertAlmostEqual(no_bookmark_load(0.0, 300.0), 2000 * 100.0 / 100.0 / 450.0)
        lam = math.log(2000 * 100.0 / 100.0 / 450.0) / 300.0
        self.assertAlmostEqual(no_bookmark_load(lam, 300.0), 1.0)


if __name__ == '__main__':
    unittest.main()
