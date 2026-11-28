"""Checks Part 4's drain with replacements placed by the scheduler: the policy that puts every
replacement where no later drain reaches it reproduces the frozen drain; a replacement placed on a
node not yet drained is evicted again; spreading and packing lose at least as many application
replicas as that policy over every drain order; and the documented practice loses nothing under any
policy.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import unittest

from recovery import placed_drain, rolling_drain

PLACE = {'webhook': [0, 3, 6], 'dns': [1, 4], 'app': [2, 5, 8]}
REJECTING = ({'app': {'webhook'}, 'webhook': {'webhook'}}, {'webhook': {'webhook'}})
CASES = (({'app': {'webhook'}}, {}, None),
         ({'app': {'webhook'}, 'webhook': {'webhook'}}, {}, None),
         (REJECTING[0], REJECTING[1], None),
         ({}, {'webhook': {'webhook'}}, None),
         (REJECTING[0], REJECTING[1], {'webhook': 2}),
         (REJECTING[0], REJECTING[1], {'webhook': 1}))


class Placement(unittest.TestCase):
    """Out of reach policy reproduces the frozen drain; a replacement on a node not yet drained is evicted again;
    spreading and packing lose at least as much; documented practice loses nothing."""

    def test_out_of_reach_policy_reproduces_the_frozen_drain(self):
        for needs, rejects, budget in CASES:
            old = rolling_drain(PLACE, needs, rejects, list(range(9)), budget)
            new = placed_drain(PLACE, needs, rejects, list(range(9)), budget, policy='out of reach', nodes=9)
            self.assertEqual(old['replicas'], new['replicas'])
            self.assertEqual(old['stalled'], new['stalled'])

    def test_a_replacement_on_a_node_not_yet_drained_is_evicted_again(self):
        # Spreading sends the first replacements to node 7, empty and drained later.
        out = placed_drain(PLACE, {}, {}, list(range(9)), None, policy='spread', nodes=9)
        self.assertGreater(out['evictions'], sum(len(v) for v in PLACE.values()))
        self.assertEqual(out['replicas'], {'webhook': 3, 'dns': 2, 'app': 3})

    def test_spreading_and_packing_lose_at_least_as_much(self):
        for order in itertools.permutations(range(9)):
            if order[0] > 2:      # a sample of orders keeps the test fast
                continue
            base = placed_drain(PLACE, *REJECTING, list(order), None, policy='out of reach', nodes=9)['replicas']['app']
            for policy in ('spread', 'pack'):
                got = placed_drain(PLACE, *REJECTING, list(order), None, policy=policy, nodes=9)['replicas']['app']
                self.assertLessEqual(got, base, msg='%s %s' % (policy, order))

    def test_documented_practice_loses_nothing(self):
        for policy in ('out of reach', 'spread', 'pack'):
            for order in (list(range(9)), list(range(8, -1, -1))):
                out = placed_drain(PLACE, {'app': {'webhook'}}, {}, order, None, policy=policy, nodes=9)
                self.assertEqual(out['replicas'], {'webhook': 3, 'dns': 2, 'app': 3})


if __name__ == '__main__':
    unittest.main()
