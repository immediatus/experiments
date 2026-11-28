"""Checks Part 2's formal side over surges from 3x to 100x. In isolation each loop meets a deadline: with
ample nodes the pod loop meets R tau_pod plus a sync period per round, and with a node loop that sees the
final need the pair meets R tau_pod + tau_node plus a sync and a scan per round. Nested, the pair is still
live, capacity always meets the surge, but no surge of two or more rounds meets the separated deadline:
each takes at least R (tau_pod + tau_node).

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import rounds
from nested import simulate

SURGES = [3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30, 40, 50, 64, 80, 100]


class Deadline(unittest.TestCase):
    """Pod loop alone meets its deadline; separated pair meets its deadline; nested pair is live and late."""

    def test_pod_loop_alone_meets_its_deadline(self):
        for k in SURGES:
            r = rounds(k)
            self.assertLessEqual(simulate(k, headroom=10 ** 5), r * (90 + 15))

    def test_separated_pair_meets_its_deadline(self):
        for k in SURGES:
            r = rounds(k)
            self.assertLessEqual(simulate(k, oracle=True), r * (90 + 15 + 10) + 210)

    def test_nested_pair_is_live_and_late(self):
        for k in SURGES:
            r = rounds(k)
            t = simulate(k)
            self.assertIsNotNone(t)
            self.assertGreaterEqual(t, r * (90 + 210))
            if r >= 2:
                self.assertGreater(t, r * (90 + 15 + 10) + 210)


if __name__ == '__main__':
    unittest.main()
