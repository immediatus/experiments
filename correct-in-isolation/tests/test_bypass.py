"""Checks Part 4's stuck eviction under the documented remedies: an operator who deletes the pod
directly at each stall, as the eviction guide suggests, takes the drain to the same end as no budget
at all; the unhealthy-pod eviction policy does not change the stall, because a rejected replacement
is never a pod.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import unittest

from recovery import rolling_drain

PLACE = {'webhook': [0, 3, 6], 'dns': [1, 4], 'app': [2, 5, 8]}
NEEDS, REJECTS = {'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}}


class Bypass(unittest.TestCase):
    """Deleting at each stall ends as no budget; stalls counted."""

    def test_deleting_at_each_stall_ends_as_no_budget(self):
        for budget in (1, 2):
            for order in itertools.permutations(range(9)):
                if order[0] > 1:
                    continue
                order = list(order)
                bypassed = rolling_drain(PLACE, NEEDS, REJECTS, order, {'webhook': budget}, bypass=True)
                none = rolling_drain(PLACE, NEEDS, REJECTS, order, None)
                self.assertEqual(bypassed['replicas'], none['replicas'])
                self.assertIsNone(bypassed['stalled'])

    def test_stalls_counted(self):
        out = rolling_drain(PLACE, NEEDS, REJECTS, list(range(9)), {'webhook': 2}, bypass=True)
        self.assertEqual(out['bypassed'], [3, 6])
        out = rolling_drain(PLACE, NEEDS, REJECTS, list(range(9)), {'webhook': 1}, bypass=True)
        self.assertEqual(out['bypassed'], [6])


if __name__ == '__main__':
    unittest.main()
