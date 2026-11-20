"""Checks Part 3's formal side and its controller. In a storm both safeguards keep their contracts: every
admitted request starts within the wait limit, and no informer answered 410 more than an hour before the
end is still without its list, so each informer keeps re-syncing. A controller that reads the rate of 410s
and, above a threshold, moves lists to a priority level of their own (a share of the seats) cuts the shared
delay: re-watches stop queueing behind lists, and the storm ends. Released as soon as the 410s stop, it hunts; held for a while, it does not.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from relist import simulate_limited

CTRL = {'on_rate': 0.1, 'window': 60.0, 'period': 10.0, 'hold': 1800.0, 'share': 0.5}


class Contracts(unittest.TestCase):

    def test_storm_keeps_both_contracts(self):
        out = simulate_limited(114.0)
        extra = out[6]
        self.assertGreater(out[0][-1], 3000)
        self.assertLessEqual(extra['worst_admitted_wait'], 15.0 + 1e-9)
        self.assertGreaterEqual(min(extra['lists']), 1)
        self.assertEqual(extra['stranded'], 0)

    def test_default_is_unchanged(self):
        out = simulate_limited(114.0)
        self.assertEqual(out[1], 23656)
        self.assertEqual(out[6]['switches'], 0)


class Cascade(unittest.TestCase):

    def test_forced_clients_are_reported(self):
        out = simulate_limited(150.0, waves=[(0.0, 1.0 / 3.0)])[6]
        self.assertEqual(len(out['forced']), 2000)
        share = sum(out['forced']) / 2000.0
        self.assertLess(abs(share - 1.0 / 3.0), 0.05)

    def test_storm_spreads_to_informers_never_forced(self):
        out = simulate_limited(150.0, waves=[(0.0, 1.0 / 3.0)])[6]
        unforced_gone = sum(g for g, f in zip(out['gone'], out['forced']) if not f)
        self.assertGreater(unforced_gone, 0)


class Split(unittest.TestCase):

    def test_static_split_ends_the_storm(self):
        out = simulate_limited(114.0, controller=dict(CTRL, on_rate=0.0, hold=1e12))
        self.assertEqual(out[6]['gone_per_hour'][-1], 0)

    def test_controller_ends_the_storm(self):
        out = simulate_limited(114.0, controller=CTRL)
        self.assertEqual(out[6]['gone_per_hour'][-1], 0)
        self.assertLess(out[0][-1], 100)
        self.assertGreaterEqual(out[6]['switches'], 1)

    def test_release_without_hold_hunts(self):
        held = simulate_limited(114.0, controller=CTRL)
        hunting = simulate_limited(114.0, controller=dict(CTRL, hold=0.0))
        self.assertGreater(hunting[6]['switches'], held[6]['switches'])
        self.assertGreater(hunting[1], held[1])

    def test_split_time_is_reported(self):
        self.assertEqual(simulate_limited(114.0)[6]['split_seconds'], 0.0)
        held = simulate_limited(114.0, controller=CTRL)[6]['split_seconds']
        self.assertGreater(held, CTRL['hold'])
        self.assertGreater(held, simulate_limited(114.0, controller=dict(CTRL, hold=600.0))[6]['split_seconds'])

    def test_controller_idle_without_a_trigger(self):
        out = simulate_limited(114.0, forced=0.0, controller=CTRL)
        self.assertEqual(out[6]['switches'], 0)


if __name__ == '__main__':
    unittest.main()
