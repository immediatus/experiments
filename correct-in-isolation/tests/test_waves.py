"""Checks Part 3's rolling restart: a trigger in waves, each wave forcing a share of the informers to
list at its own time (the informers that resume against one restarted server). One wave of everyone
at time zero is the sudden full trigger; waves forcing nobody are no trigger.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from relist import simulate_limited


class Waves(unittest.TestCase):

    def test_one_wave_of_everyone_is_the_full_trigger(self):
        for cost in (40.0, 114.0):
            self.assertEqual(simulate_limited(cost, waves=((0.0, 1.0),), hours=3)[:3],
                             simulate_limited(cost, forced=1.0, hours=3)[:3])

    def test_three_simultaneous_thirds_storm_like_one_full_trigger(self):
        r = simulate_limited(120.0, waves=((0.0, 1 / 3), (0.0, 1 / 3), (0.0, 1 / 3)), hours=8)
        self.assertGreater(r[0][-1], 0.9 * 100 / 120 * 3600)

    def test_waves_are_disjoint(self):
        r = simulate_limited(10.0, waves=((0.0, 0.5), (600.0, 0.5)), hours=2)
        self.assertEqual(sum(r[0]), 2000)


if __name__ == '__main__':
    unittest.main()
