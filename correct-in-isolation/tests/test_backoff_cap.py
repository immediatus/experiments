"""Checks Part 4's configurable kubelet backoff (KubeletCrashLoopBackOffMax, beta and on by default
since Kubernetes 1.35: maxContainerRestartPeriod from 1 s to 300 s per node; the alpha
ReduceDefaultCrashLoopBackOffDecay starts at 1 s and caps at 60 s): the cold-start chain with the
default cap is unchanged, and a lower cap bounds how late the webhook can start, without making
every case faster.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import cold_start_chain


class BackoffCap(unittest.TestCase):
    """Default cap is the documented chain; the cap bounds the lateness not every case; a lower cap lowers the worst
    ratio; a cap below the base starts at the cap."""

    def test_default_cap_is_the_documented_chain(self):
        for dns in (30.0, 300.0, 1200.0):
            self.assertEqual(cold_start_chain(dns, cap=300.0, base=10.0), cold_start_chain(dns))

    def test_the_cap_bounds_the_lateness_not_every_case(self):
        # restart times under two caps do not nest, so a lower cap can be later at one DNS time
        self.assertGreater(cold_start_chain(190.0, cap=60.0)['webhook_ready'], cold_start_chain(190.0)['webhook_ready'])
        for cap in (300.0, 120.0, 60.0, 10.0):
            for dns in range(30, 1201, 5):
                out = cold_start_chain(float(dns), cap=cap)
                self.assertLessEqual(out['webhook_ready'] - out['webhook_ready_ideal'], cap + 5.0)

    def test_a_lower_cap_lowers_the_worst_ratio(self):
        def worst(cap):
            return max(o['app_ready'] / o['app_ready_ideal'] for o in (cold_start_chain(float(d), cap=cap) for d in range(30, 1201, 15)))
        self.assertGreater(worst(300.0), worst(120.0))
        self.assertGreater(worst(120.0), worst(60.0))

    def test_a_cap_below_the_base_starts_at_the_cap(self):
        a = cold_start_chain(100.0, cap=2.0)['webhook_ready']
        b = cold_start_chain(100.0, cap=2.0, base=2.0)['webhook_ready']
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
