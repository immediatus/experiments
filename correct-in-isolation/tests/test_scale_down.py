"""Checks the second-surge extension of Part 2's model: while the pod loop's stabilization window
holds the surge's pods, a second surge is served at once; after it, the nodes the scale-down
leaves behind act as headroom for the rounds placed before the node loop deletes them, so the time
is R tau_pod + (R - m) tau_node with m those rounds; and, for a known gap, every unneeded-time
between releasing at once and holding through the gap is dominated. Deletion is made instant
(an unbounded bulk) so the boundaries are sharp; the documented bulk of 10 is reported (T28).

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import kept_rounds, rounds, second_surge_time
from nested import simulate_two_surges

LATENCY = 15 + 10 + 5   # one sync period, one scan interval and one time step, per round
INSTANT = 10 ** 6


class SecondSurge(unittest.TestCase):
    """Inside the stabilization window the pods are still there; kept rounds counts rounds placed before deletion;
    simulation matches the closed form away from the boundaries; the closed form spans ample to nested; partial
    holding is dominated for a known gap."""

    def test_inside_the_stabilization_window_the_pods_are_still_there(self):
        for gap in (0, 60, 150, 240, 280):
            self.assertEqual(simulate_two_surges(gap, bulk=INSTANT)[0], 0)
            self.assertEqual(second_surge_time(gap, 30, 90, 210), 0)

    def test_kept_rounds_counts_rounds_placed_before_deletion(self):
        # S + U = 900 s; rounds are placed at G, G + 90, G + 180, G + 270
        self.assertEqual([kept_rounds(g, 30, 90) for g in (300, 600, 675, 765, 855, 945)], [4, 4, 3, 2, 1, 0])

    def test_simulation_matches_the_closed_form_away_from_the_boundaries(self):
        for gap in (330, 450, 585, 675, 765, 855, 945, 1200, 3600):
            sim, _ = simulate_two_surges(gap, bulk=INSTANT)
            closed = second_surge_time(gap, 30, 90, 210)
            self.assertGreaterEqual(sim, closed - LATENCY, gap)
            self.assertLessEqual(sim, closed + rounds(30) * LATENCY, gap)

    def test_the_closed_form_spans_ample_to_nested(self):
        self.assertEqual(second_surge_time(450, 30, 90, 210), 4 * 90)
        self.assertEqual(second_surge_time(3600, 30, 90, 210), 4 * (90 + 210))

    def test_partial_holding_is_dominated_for_a_known_gap(self):
        gap = 1200
        release = simulate_two_surges(gap, unneeded=0, bulk=INSTANT)
        hold = simulate_two_surges(gap, unneeded=1800, bulk=INSTANT)
        self.assertLess(hold[0], release[0])
        self.assertLess(release[1], hold[1])
        for u in (60, 300, 600, 900, 1000, 1080, 1140):
            t, held = simulate_two_surges(gap, unneeded=u, bulk=INSTANT)
            by_release = t >= release[0] and held > release[1]
            by_hold = t > hold[0] and held >= hold[1]
            self.assertTrue(by_release or by_hold, (u, t, held))


if __name__ == '__main__':
    unittest.main()
