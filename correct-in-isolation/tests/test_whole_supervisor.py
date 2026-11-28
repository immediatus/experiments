"""Checks Part 6's whole-system supervisor on the signal and time-scale seams, the pair that shares settings.
A greedy supervisor takes the seams in order of their ratios and gives each the smallest change of one setting
that brings its own ratio to one: headroom for the time scale, then the target moved into the rest band for the
signal. The second fix lowers the growth factor, so the first one no longer covers the rounds. A fix that moves the
target or the tolerance keeps the demand. A coupling-aware supervisor chooses the signal fix by its effect on both
ratios, and with it the headroom; without the load metric the tolerance beats the band target on slots and time.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from supervisor_whole import greedy, joint


class Greedy(unittest.TestCase):
    """Second fix reopens the first seam; moving the target keeps the demand; every fix carries the same demand."""

    def test_second_fix_reopens_the_first_seam(self):
        steps = greedy()
        self.assertEqual([s['fix'] for s in steps], ['start', 'headroom', 'target', 'headroom'])
        start, first, second, third = steps
        self.assertGreater(start['time_ratio'], start['signal_ratio'])
        self.assertLessEqual(first['time_ratio'], 1.0)
        self.assertGreater(second['time_ratio'], 1.0)
        self.assertGreater(second['surge_s'], start['surge_s'])
        self.assertLessEqual(third['time_ratio'], 1.0)
        self.assertLessEqual(third['signal_ratio'], 1.0)
        self.assertEqual(third['slots'], 218)

    def test_moving_the_target_keeps_the_demand(self):
        # the demand 16 pods carry at 0.5 is carried by 10 pods at 0.8; the surge is to 30 times that demand
        for s in greedy():
            self.assertAlmostEqual(s['pods'] * s['target'], 16 * 0.5)

    def test_every_fix_carries_the_same_demand(self):
        # the tolerance fix rests at the vertical loop's utilization, 0.87, so the same demand runs on 9 pods
        for allow, rank in ((True, 'slots'), (False, 'slots'), (False, 'time')):
            s = joint(allow_load=allow, rank=rank)
            self.assertAlmostEqual(s['pods'] * s['utilization'], 16 * 0.5, delta=0.5)


class Joint(unittest.TestCase):
    """Load metric needs no headroom; without the load metric the tolerance dominates the band target."""

    def test_load_metric_needs_no_headroom(self):
        best = joint()
        self.assertEqual(best['fix'], 'load metric')
        self.assertEqual(best['slots'], 0)
        self.assertEqual(best['surge_s'], 350)

    def test_without_the_load_metric_the_tolerance_dominates_the_band_target(self):
        # at the same demand the tolerance holds fewer slots than the greedy end and meets the surge more than
        # twice as fast, so either ranking chooses it
        greedy_end = greedy()[-1]
        for rank in ('slots', 'time'):
            best = joint(allow_load=False, rank=rank)
            self.assertEqual(best['fix'], 'scale-up tolerance')
            self.assertEqual(best['slots'], 135)
            self.assertLess(best['slots'], greedy_end['slots'])
            self.assertLess(2 * best['surge_s'], greedy_end['surge_s'])

if __name__ == '__main__':
    unittest.main()
