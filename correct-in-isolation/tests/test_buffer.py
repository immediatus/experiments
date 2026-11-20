"""Checks Part 2's capacity buffer (the Cluster Autoscaler's CapacityBuffer API, beta since 1.35):
a buffer sized as a percentage of the deployment's current replicas is held as fake pods the node
loop provisions for, so it grows with every round and refills while the surge runs.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from nested import simulate


class Buffer(unittest.TestCase):

    def test_no_buffer_is_the_plain_run(self):
        for k in (5, 30):
            self.assertEqual(simulate(k, buffer_pct=0), simulate(k))

    def test_a_buffer_beats_static_headroom_of_the_same_start(self):
        for pct in (25, 50, 100):
            start = -(-16 * pct // 100)
            self.assertLessEqual(simulate(30, buffer_pct=pct), simulate(30, headroom=start))

    def test_buffer_never_slower_than_none(self):
        base = simulate(30)
        for pct in (10, 25, 50, 100, 200, 400):
            self.assertLessEqual(simulate(30, buffer_pct=pct), base)

    def test_a_buffer_cannot_beat_ample_nodes(self):
        ample = simulate(30, headroom=10 ** 4)
        for pct in (100, 400, 3000):
            self.assertGreaterEqual(simulate(30, buffer_pct=pct), ample)


if __name__ == '__main__':
    unittest.main()
