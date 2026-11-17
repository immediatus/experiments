"""Checks Part 6's whole-system supervisor on the signal and time-scale seams, the pair that shares settings.
A greedy supervisor takes the seams in order of their ratios and gives each the smallest change of one setting
that brings its own ratio to one: headroom for the time scale, then the target moved into the rest band for the
signal. The second fix lowers the growth factor, so the first one no longer covers the rounds. A coupling-aware
supervisor chooses the signal fix by its effect on both ratios, and with it the headroom.

Run: python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from supervisor_whole import greedy, joint


class Greedy(unittest.TestCase):

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
        self.assertEqual(third['slots'], 348)


class Joint(unittest.TestCase):

    def test_load_metric_needs_no_headroom(self):
        best = joint()
        self.assertEqual(best['fix'], 'load metric')
        self.assertEqual(best['slots'], 0)
        self.assertEqual(best['surge_s'], 350)

    def test_without_the_load_metric_the_tolerance_wins(self):
        best = joint(allow_load=False)
        self.assertEqual(best['fix'], 'scale-up tolerance')
        self.assertEqual(best['slots'], 240)
        self.assertLess(best['surge_s'], greedy()[-1]['surge_s'])


if __name__ == '__main__':
    unittest.main()
