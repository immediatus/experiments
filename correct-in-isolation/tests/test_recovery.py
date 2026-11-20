"""Checks Part 4's model: recovery stops exactly at start-time cycles inside the failed set, the
per-component check passes on a cluster that never recovers, and the closed-form probability
that a failure covers a cycle matches enumeration.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import unittest

from formulas import bind_probability
from recovery import each_component_check, recover, unrecoverable_fraction

NODES = set(range(9))


class Recovery(unittest.TestCase):

    def test_without_a_cycle_every_failure_recovers(self):
        placement = {'dns': {0, 1}, 'webhook': {2, 3}, 'app': {4, 5}}
        needs = {'app': {'webhook', 'dns'}, 'webhook': {'dns'}}
        for k in range(len(NODES) + 1):
            for failed in itertools.combinations(sorted(NODES), k):
                self.assertEqual(recover(placement, needs, set(failed)), set())

    def test_a_self_matching_webhook_is_lost_only_with_all_its_replicas(self):
        placement = {'webhook': {0, 3, 6}}
        needs = {'webhook': {'webhook'}}
        self.assertEqual(recover(placement, needs, {0, 3}), set())
        self.assertEqual(recover(placement, needs, {0, 3, 6}), {'webhook'})

    def test_dependents_of_a_bound_cycle_stay_down(self):
        placement = {'dns': {0, 1}, 'webhook': {0, 1}, 'app': {2}}
        needs = {'dns': {'webhook'}, 'webhook': {'dns'}, 'app': {'webhook'}}
        self.assertEqual(recover(placement, needs, {0, 1, 2}), {'dns', 'webhook', 'app'})
        self.assertEqual(recover(placement, needs, {0, 2}), set())

    def test_each_component_check_passes_where_the_cluster_never_recovers(self):
        placement = {'webhook': {0, 1, 2}}
        needs = {'webhook': {'webhook'}}
        self.assertEqual(recover(placement, needs, NODES), {'webhook'})
        self.assertTrue(each_component_check(placement, needs, NODES))

    def test_bind_probability_matches_enumeration(self):
        for u in (1, 2, 3, 4):
            placement = {'webhook': set(range(u))}
            for k in range(len(NODES) + 1):
                self.assertAlmostEqual(unrecoverable_fraction(placement, {'webhook': {'webhook'}}, NODES, k),
                                       bind_probability(len(NODES), u, k), places=12)


if __name__ == '__main__':
    unittest.main()
