"""Checks Part 3's model: each safeguard alone never re-lists beyond the trigger, the composite
starts a second wave exactly past the closed-form threshold, no storm sustains itself below
the necessary condition, and a sustained storm spends all capacity on LISTs.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import failed_list_rate, failed_state_possible, second_wave
from relist import simulate

N, C, R, SHORT, MEAN = 2000, 100.0, 300.0, 300.0, 450.0


class EachSafeguardAlone(unittest.TestCase):
    """Ample capacity lists only the forced clients; unbounded history lists only the forced clients; no trigger no
    list."""

    def test_ample_capacity_lists_only_the_forced_clients(self):
        per_hour, _ = simulate(100.0, capacity=C * 100)
        self.assertEqual(sum(per_hour), N)

    def test_unbounded_history_lists_only_the_forced_clients(self):
        per_hour, _ = simulate(100.0, retention=10 ** 9)
        self.assertEqual(sum(per_hour), N)

    def test_no_trigger_no_list(self):
        per_hour, _ = simulate(100.0, forced=0.0)
        self.assertEqual(sum(per_hour), 0)


class Composite(unittest.TestCase):
    """No second wave at or below the threshold; second wave above the threshold; no sustained storm below the
    necessary condition; sustained storm spends all capacity on lists."""

    def test_no_second_wave_at_or_below_the_threshold(self):
        for seed in (1, 2, 3):
            self.assertFalse(second_wave(30.0, N, C, R, SHORT))
            self.assertEqual(sum(simulate(30.0, hours=3, seed=seed)[0]), N)

    def test_second_wave_above_the_threshold(self):
        self.assertTrue(second_wave(40.0, N, C, R, SHORT))
        self.assertGreater(sum(simulate(40.0, hours=3)[0]), N)

    def test_no_sustained_storm_below_the_necessary_condition(self):
        for cost in (40.0, 50.0):
            self.assertFalse(failed_state_possible(cost, N, C, R, MEAN))
            for spread in (0.0, 450.0, 900.0):
                for seed in (1, 2):
                    self.assertEqual(simulate(cost, spread=spread, seed=seed)[0][-1], 0)

    def test_sustained_storm_spends_all_capacity_on_lists(self):
        per_hour, _ = simulate(100.0)
        expected = failed_list_rate(100.0, C) * 3600
        for count in per_hour[1:]:
            self.assertLess(abs(count / expected - 1.0), 0.02)


if __name__ == '__main__':
    unittest.main()
