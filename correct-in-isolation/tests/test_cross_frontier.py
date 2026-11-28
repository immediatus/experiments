"""Checks the cross-seam frontier of Part 6. On a shared CPU metric with the limit equal to the request,
a pair at rest holds the vertical loop's utilization v = 1/((1+m)q). With a per-direction scale-up
tolerance v/u_h - 1, every horizontal target u_h <= v rests the pair, and a surge to k times the resting
demand then needs ceil(ln(k v) / ln(1/u_h)) rounds: the target sets only the growth factor. So zero drift
would seem compatible with any surge speed the target can buy. It is not: the round's first action
doubles the replicas at most, the ratio then counts the new pods at zero, and the matched tolerance blocks
every further action in the round, so the growth per round is min(1/u_h, 2) and a resting pair needs at
least ceil(ln(k v) / ln 2) rounds, 5 for a thirtyfold surge, whatever its target.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import matched_tolerance, resting_rounds, vpa_utilisation
from hpa_vpa import simulate as pair
from nested import simulate as nested

V = vpa_utilisation()


def surge_from_rest(u_h, k=30.0):
    """Seconds to meet a surge to k times the demand a pair resting at target u_h carries, with the matched scale-up
    tolerance."""
    return nested(k * V / u_h, target=u_h, tol=matched_tolerance(u_h))


class Closed(unittest.TestCase):
    """Matched tolerance puts rest at the scale up edge; rounds at a half; rounds have a floor at the policy
    doubling."""

    def test_matched_tolerance_puts_rest_at_the_scale_up_edge(self):
        self.assertAlmostEqual(0.5 * (1 + matched_tolerance(0.5)), V, places=9)

    def test_rounds_at_a_half(self):
        self.assertEqual(resting_rounds(30, 0.5), 5)

    def test_rounds_have_a_floor_at_the_policy_doubling(self):
        self.assertEqual(resting_rounds(30, 0.3), 5)
        self.assertLess(resting_rounds(30, 0.5), resting_rounds(30, 0.8))


class Simulated(unittest.TestCase):
    """Half target matches the frozen tolerance fix; surge from rest has a floor; a drifting pair beats the floor;
    matched tolerance stops the drift."""

    def test_half_target_matches_the_frozen_tolerance_fix(self):
        self.assertEqual(surge_from_rest(0.5), 1500)

    def test_surge_from_rest_has_a_floor(self):
        for u_h in (0.3, 0.4, 0.5):
            self.assertEqual(surge_from_rest(u_h), resting_rounds(30, u_h) * 300)
        for u_h in (0.55, 0.6, 0.7):
            self.assertEqual(surge_from_rest(u_h), resting_rounds(30, u_h) * 300)

    def test_a_drifting_pair_beats_the_floor(self):
        self.assertLess(nested(30, target=0.3), surge_from_rest(0.3))

    def test_matched_tolerance_stops_the_drift(self):
        for u_h in (0.4, 0.6):
            samples = pair(u_h, days=60, tol_up=matched_tolerance(u_h) + 0.01)[0]
            self.assertLess(samples[-1][1], 1.5 * samples[0][1])


if __name__ == '__main__':
    unittest.main()
