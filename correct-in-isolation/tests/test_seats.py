"""Checks Part 3's prices in seats. API Priority and Fairness divides the server's concurrency, the sum
of --max-requests-inflight (400) and --max-mutating-requests-inflight (200), among priority levels by
nominal shares, rounding up; a level lets one request take at most max(1, min(ceil(0.15 CL), CL /
handSize)) seats. With SizeBasedListCostEstimate a list costs ceil(bytes / 100,000) seats, its bytes
capped at 1,000,000 when served from the watch cache, and at most 100 seats and the level's maximum.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import level_limits, list_seats, list_time_threshold


class Seats(unittest.TestCase):
    """Default levels; cache caps a list at ten seats; storage lists take more; time threshold scales with capacity."""

    def test_default_levels(self):
        levels = level_limits()
        self.assertEqual(levels['system'], (74, 12))
        self.assertEqual(levels['workload-low'], (245, 37))
        self.assertEqual(levels['global-default'], (49, 8))

    def test_cache_caps_a_list_at_ten_seats(self):
        self.assertEqual(list_seats(150000, 20000, from_cache=True, level_max=37), 10)
        self.assertEqual(list_seats(10, 2000, from_cache=True, level_max=37), 1)

    def test_storage_lists_take_more(self):
        self.assertEqual(list_seats(150000, 20000, from_cache=False, level_max=37), 37)
        self.assertEqual(list_seats(150000, 20000, from_cache=False, level_max=200), 100)

    def test_time_threshold_scales_with_capacity(self):
        a = list_time_threshold(5000, 10, 245, 750.0)
        self.assertAlmostEqual(a, 750.0 * 245 / (5000 * 10))
        self.assertAlmostEqual(list_time_threshold(5000, 10, 490, 750.0), 2 * a)


if __name__ == '__main__':
    unittest.main()
