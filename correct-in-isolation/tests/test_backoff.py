"""Checks Part 4's cold start through two documented backoffs: a ReplicaSet whose creations a webhook
rejects retries at 5 ms (2^k - 1), so it next tries before twice the outage plus 5 ms; a container
that crashes until a dependency is up restarts after 10, 20, 40 s and so on, capped at 300 s; and a
chain through both is ready no earlier than with instant retries.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import cold_start_chain, kubelet_start_after, workqueue_retry_after


class Backoffs(unittest.TestCase):

    def test_workqueue_retry_within_twice_the_outage(self):
        for t in (0.001, 0.5, 3.0, 30.0, 90.0, 299.0, 600.0):
            r = workqueue_retry_after(t)
            self.assertGreaterEqual(r, t)
            self.assertLess(r, 2 * t + 0.005 + 1e-9)

    def test_workqueue_cap_bounds_the_wait(self):
        for t in (5000.0, 20000.0):
            self.assertLessEqual(workqueue_retry_after(t) - t, 1000.0 + 1e-9)

    def test_kubelet_schedule(self):
        # first start at 30, each attempt runs 5 s: starts at 30, 45, 70, 115, 200, ...
        self.assertEqual(kubelet_start_after(90.0, first_start=30.0, run=5.0), 115.0)
        self.assertEqual(kubelet_start_after(10.0, first_start=30.0, run=5.0), 30.0)
        self.assertLessEqual(kubelet_start_after(5000.0, first_start=0.0, run=5.0) - 5000.0, 305.0)

    def test_chain_not_faster_than_instant_retries(self):
        for dns in (30.0, 90.0, 300.0, 600.0):
            out = cold_start_chain(dns)
            self.assertGreaterEqual(out['app_ready'], out['app_ready_ideal'])
            self.assertGreaterEqual(out['webhook_ready'], out['webhook_ready_ideal'])


if __name__ == '__main__':
    unittest.main()
