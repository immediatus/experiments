"""Checks the rolling-drain extension of the recovery model. An availability edge (a webhook with
failurePolicy Fail that must be up to admit a pod) does not stop a rolling drain, because the other
replicas are up when each one is replaced. A rejection edge (a running webhook whose rules reject the
pod) stops every replacement while that webhook runs. Without a disruption budget one drain of every
node removes the component under Fail, and every later pod of what needs it is rejected; under Ignore
the last replica's replacement is admitted while the webhook is down, so it survives with one replica
and still cannot heal. With a budget of minAvailable m the drain stalls after n - m evictions, the
documented "stuck evictions". Replacements land on nodes already drained and back from upgrade.

Run: python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import math
import unittest

from recovery import drain_losses, rolling_drain

NODES = list(range(9))
PLACE = {'webhook': [0, 3, 6], 'dns': [1, 4], 'app': [2, 5, 8]}


class RollingDrain(unittest.TestCase):

    def test_availability_edges_survive_a_rolling_drain(self):
        out = rolling_drain(PLACE, needs={'app': {'webhook'}, 'webhook': {'webhook'}}, rejects={}, order=NODES)
        self.assertIsNone(out['stalled'])
        self.assertEqual(out['replicas'], {'webhook': 3, 'dns': 2, 'app': 3})

    def test_a_rejection_edge_removes_the_component_and_what_needs_it(self):
        out = rolling_drain(PLACE, needs={'app': {'webhook'}, 'webhook': {'webhook'}}, rejects={'webhook': {'webhook'}}, order=NODES)
        self.assertIsNone(out['stalled'])
        self.assertEqual(out['replicas']['webhook'], 0)
        self.assertEqual(out['replicas']['app'], 2)      # its replica on node 8 is drained after the webhook's last
        self.assertEqual(out['replicas']['dns'], 2)

    def test_failure_policy_ignore_keeps_one_replica_and_no_more(self):
        out = rolling_drain(PLACE, needs={}, rejects={'webhook': {'webhook'}}, order=NODES)
        self.assertEqual(out['replicas']['webhook'], 1)

    def test_a_budget_stalls_the_drain_after_n_minus_m_evictions(self):
        for m in (1, 2):
            out = rolling_drain(PLACE, needs={'webhook': {'webhook'}}, rejects={'webhook': {'webhook'}}, order=NODES,
                                min_available={'webhook': m})
            self.assertEqual(out['replicas']['webhook'], m)
            self.assertEqual(out['stalled'], PLACE['webhook'][3 - m])
            self.assertEqual(drain_losses(3, m), 3 - m)

    def test_the_documented_fix_removes_the_edge(self):
        out = rolling_drain(PLACE, needs={'app': {'webhook'}}, rejects={}, order=NODES, min_available={'webhook': 2})
        self.assertIsNone(out['stalled'])
        self.assertEqual(out['replicas'], {'webhook': 3, 'dns': 2, 'app': 3})


if __name__ == '__main__':
    unittest.main()


class FiniteLife(unittest.TestCase):

    def test_expected_life_is_the_harmonic_number_over_the_failure_rate(self):
        from formulas import rejection_life
        self.assertAlmostEqual(rejection_life(1, 30.0), 30.0)
        self.assertAlmostEqual(rejection_life(3, 30.0), 30.0 * (1 + 1 / 2 + 1 / 3))

    def test_simulated_life_matches(self):
        from formulas import rejection_life
        from recovery import simulated_life
        for n in (1, 3, 5):
            sim = simulated_life(n, 30.0, runs=20000)
            self.assertLess(abs(sim / rejection_life(n, 30.0) - 1), 0.02, n)

    def test_drain_order_decides_what_the_app_loses(self):
        from recovery import drain_order_losses
        dist = drain_order_losses(PLACE, needs={'app': {'webhook'}, 'webhook': {'webhook'}},
                                  rejects={'webhook': {'webhook'}}, orders=2000)
        self.assertEqual(sum(dist.values()), 2000)
        self.assertTrue(set(dist) <= {0, 1, 2, 3})
        self.assertGreater(len(dist), 1)


class DrainOrder(unittest.TestCase):

    def test_closed_form_matches_random_orders(self):
        from formulas import app_loss_distribution
        from recovery import drain_order_losses
        closed = app_loss_distribution(3, 3)
        self.assertAlmostEqual(math.fsum(closed.values()), 1.0)
        self.assertEqual([round(closed[j], 2) for j in range(4)], [0.5, 0.3, 0.15, 0.05])
        sim = drain_order_losses(PLACE, needs={'app': {'webhook'}, 'webhook': {'webhook'}},
                                 rejects={'webhook': {'webhook'}}, orders=20000)
        for j in range(4):
            self.assertLess(abs(sim.get(j, 0) / 20000 - closed[j]), 0.01, j)

    def test_expected_loss(self):
        from formulas import app_loss_distribution
        for na, nw in ((3, 3), (5, 2), (2, 5)):
            d = app_loss_distribution(na, nw)
            self.assertAlmostEqual(math.fsum(j * p for j, p in d.items()), na / (nw + 1))
