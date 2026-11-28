"""Checks Part 3's history band: the watch cache keeps at least its event-fresh duration and, at a
steady event rate, settles between that and four times it; a shorter history lowers every
threshold, and at the specimen's list cost of 100 a history of 150 seconds sustains a storm where
300 seconds does not.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import pages_before_expiry, rejections_before_gone, watch_cache_span
from relist import simulate_limited


class WatchCacheSpan(unittest.TestCase):
    """Steady rate settles in the band; capacity bounds push outside the band."""

    def test_steady_rate_settles_in_the_band(self):
        for rate in (1.0, 3.0, 10.0, 50.0, 300.0):
            span = watch_cache_span(rate)
            self.assertGreaterEqual(span, 75.0)
            self.assertLess(span, 300.0)

    def test_capacity_bounds_push_outside_the_band(self):
        self.assertGreater(watch_cache_span(0.1), 300.0)   # 100 events at the lower bound
        self.assertLess(watch_cache_span(5000.0), 75.0)    # 102400 events at the upper bound


class Isolation(unittest.TestCase):
    """Onset scales with the level share."""

    def test_onset_scales_with_the_level_share(self):
        def storms(c, cap):
            return simulate_limited(float(c), capacity=cap)[0][-1] > 0
        self.assertTrue(storms(56, 50.0))
        self.assertFalse(storms(55, 50.0))
        self.assertTrue(storms(29, 25.0))
        self.assertFalse(storms(28, 25.0))


class Pages(unittest.TestCase):
    """Pages within the history."""

    def test_pages_within_the_history(self):
        self.assertEqual(pages_before_expiry(300.0), (20, 10000))
        self.assertEqual(pages_before_expiry(150.0), (10, 5000))
        self.assertEqual(pages_before_expiry(75.0), (5, 2500))


class ShorterHistory(unittest.TestCase):
    """Fewer rejections reach a 410; the specimen storms with 150 seconds."""

    def test_fewer_rejections_reach_a_410(self):
        self.assertEqual(rejections_before_gone(300.0), 4)
        self.assertEqual(rejections_before_gone(150.0), 2)
        self.assertEqual(rejections_before_gone(75.0), 1)

    def test_the_specimen_storms_with_150_seconds(self):
        self.assertEqual(simulate_limited(100.0, retention=300.0)[0][-1], 0)
        self.assertGreater(simulate_limited(100.0, retention=150.0)[0][-1], 0)


if __name__ == '__main__':
    unittest.main()
