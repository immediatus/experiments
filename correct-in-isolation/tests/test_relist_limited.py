"""Checks Part 3's model with the mechanisms the documented queue leaves to the implementation:
the API server's queue wait limit (15 s, then 429) and the Reflector's backoff, with one FIFO
queue and with APF fair queuing at the "system" level's defaults. Each safeguard alone still
re-lists only the forced clients; every 410 comes after at least the closed-form number of
consecutive rejections; a saturated storm needs the backlog to exceed the mean watch period plus
the retention; and a sustained storm spends all capacity on LISTs.

Run: python3 -m unittest discover -s tests
"""
import os
import random
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import failed_list_rate, fresh_rejections_to_pass, rejections_before_gone, saturated_storm_possible
from relist import ReflectorBackoff, simulate_fair, simulate_limited

N, C, R, MEAN = 2000, 100.0, 300.0, 450.0
MODELS = (simulate_limited, simulate_fair)


class Backoff(unittest.TestCase):

    def test_reflector_sequence(self):
        b = ReflectorBackoff(random.Random(1), jitter=0.0)
        self.assertEqual([b.step(0.0) for _ in range(8)], [0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 30.0, 30.0])

    def test_reset_after_two_minutes_since_the_last_reset(self):
        b = ReflectorBackoff(random.Random(1), jitter=0.0)
        b.step(0.0)
        b.step(10.0)
        b.step(20.0)
        self.assertEqual(b.step(121.0), 0.8)

    def test_jitter_stays_within_one_to_two_times(self):
        b = ReflectorBackoff(random.Random(3))
        for _ in range(50):
            d = b.duration
            self.assertTrue(d <= b.step(0.0) < 2 * d)


class EachSafeguardAlone(unittest.TestCase):

    def test_ample_capacity_lists_only_the_forced_clients(self):
        for sim in MODELS:
            self.assertEqual(sum(sim(100.0, capacity=C * 100, hours=4)[0]), N)

    def test_unbounded_history_lists_only_the_forced_clients(self):
        for sim in MODELS:
            self.assertEqual(sum(sim(100.0, retention=10 ** 9, hours=4)[0]), N)

    def test_no_trigger_no_list(self):
        for sim in MODELS:
            self.assertEqual(sum(sim(100.0, forced=0.0, hours=4)[0]), 0)


class Composite(unittest.TestCase):

    def test_fresh_backoff_needs_eleven_to_fifteen_rejections(self):
        # over every jitter pattern: a smaller jitter early postpones the two-minute reset and lets the
        # capped delays run longer, so the fewest is 11, not the 13 that the largest jitter throughout gives;
        # the P model of tla's sibling folder p/ found the 11
        fewest, most = fresh_rejections_to_pass(R)
        self.assertEqual((fewest, most), (11, 15))
        self.assertGreaterEqual(fewest, rejections_before_gone(R))

    def test_every_410_follows_the_closed_form_run_of_rejections(self):
        self.assertEqual(rejections_before_gone(R), 4)
        for sim in MODELS:
            for cost in (40.0, 100.0, 150.0):
                runs = sim(cost, hours=3)[4]
                self.assertIsNotNone(runs)
                self.assertGreaterEqual(runs[0], rejections_before_gone(R))

    def test_no_saturated_storm_below_the_necessary_condition(self):
        self.assertFalse(saturated_storm_possible(37.0, N, C, R, MEAN))
        for sim in MODELS:
            for spread in (0.0, 900.0):
                self.assertEqual(sim(37.0, spread=spread)[0][-1], 0)

    def test_sustained_storm_spends_all_capacity_on_lists(self):
        for sim in MODELS:
            per_hour = sim(150.0)[0]
            expected = failed_list_rate(150.0, C) * 3600
            for count in per_hour[1:]:
                self.assertLess(abs(count / expected - 1.0), 0.02)

    def test_onset_of_the_sustained_storm(self):
        """Reported, and pinned so a change to the model is noticed: none at 112, sustained at 116."""
        for sim in MODELS:
            self.assertEqual(sim(112.0)[0][-1], 0)
            self.assertGreater(sim(116.0)[0][-1], 0)


if __name__ == '__main__':
    unittest.main()
