"""Checks Part 4's self-upgrade: a webhook that rejects its own pods rolls out a new version under the
Deployment defaults (maxUnavailable 25% rounded down, maxSurge 25% rounded up); the old ReplicaSet is
scaled down by maxUnavailable at once, every new pod is rejected, and the rollout stalls with
n - floor(n / 4) replicas, which then last the harmonic number of that count times a node's mean time
between failures.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import rejection_life, stalled_rollout


class SelfUpgrade(unittest.TestCase):

    def test_documented_rounding(self):
        self.assertEqual(stalled_rollout(3), {'old': 3, 'new': 0, 'new_desired': 1})
        self.assertEqual(stalled_rollout(4), {'old': 3, 'new': 0, 'new_desired': 2})
        self.assertEqual(stalled_rollout(10), {'old': 8, 'new': 0, 'new_desired': 5})

    def test_availability_edge_only_completes(self):
        self.assertEqual(stalled_rollout(4, rejects_own=False), {'old': 0, 'new': 4, 'new_desired': 4})

    def test_life_shortens(self):
        self.assertLess(rejection_life(stalled_rollout(8)['old'], 30.0), rejection_life(8, 30.0))


if __name__ == '__main__':
    unittest.main()
