"""Checks Part 4's heartbeat model: a kubelet renews its Lease every 10 s and after a failure retries
from 200 ms doubling to 7 s; behind a webhook that fails each call with probability q, the node is
Unknown when no renewal succeeded in the last 50 s. With q = 0 it is never Unknown, with q = 1 always;
the share of time Unknown and the rate of spells of 300 s or more rise with q.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from recovery import eviction_regime, heartbeat_unknown


class Heartbeats(unittest.TestCase):
    """Extremes; monotone in failure probability; eviction regime follows the documented rules; attempts in one
    grace window."""

    def test_extremes(self):
        self.assertEqual(heartbeat_unknown(0.0, hours=2)['unknown_share'], 0.0)
        self.assertAlmostEqual(heartbeat_unknown(1.0, hours=2)['unknown_share'], 1.0 - 50.0 / 7200.0)

    def test_monotone_in_failure_probability(self):
        shares = [heartbeat_unknown(q, hours=20, seed=3)['unknown_share'] for q in (0.5, 0.8, 0.9, 0.95)]
        self.assertEqual(shares, sorted(shares))

    def test_eviction_regime_follows_the_documented_rules(self):
        # every node unhealthy: no evictions; at least 0.55 unhealthy: stopped in a cluster of 50 or fewer,
        # 0.01 nodes per second above; otherwise 0.1 nodes per second
        self.assertEqual(eviction_regime(1.0, 100, 5.0), 0.0)
        self.assertEqual(eviction_regime(0.6, 40, 5.0), 0.0)
        self.assertAlmostEqual(eviction_regime(0.6, 100, 500.0), 36.0)
        self.assertAlmostEqual(eviction_regime(0.4, 100, 30.0), 30.0)
        self.assertAlmostEqual(eviction_regime(0.4, 100, 5000.0), 360.0)

    def test_attempts_in_one_grace_window(self):
        # after a success: renewal at 10 s, then retries 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 7, 7 s later: 10 attempts before 50 s
        self.assertEqual(heartbeat_unknown(1.0, hours=1)['attempts_per_grace'], 10)



class FailureLatency(unittest.TestCase):
    """A webhook that fails by timing out holds each failed renewal for its timeout before the backoff starts,
    so fewer attempts fit in the grace period and the node turns unknown at a lower failure probability."""

    def test_attempts_shrink_with_latency(self):
        self.assertEqual(heartbeat_unknown(1.0, hours=1, fail_after=0.0)['attempts_per_grace'], 10)
        self.assertEqual(heartbeat_unknown(1.0, hours=1, fail_after=10.0)['attempts_per_grace'], 4)

    def test_latency_raises_the_unknown_share(self):
        fast = heartbeat_unknown(0.6, hours=50, seed=2)['unknown_share']
        slow = heartbeat_unknown(0.6, hours=50, seed=2, fail_after=10.0)['unknown_share']
        self.assertGreater(slow, fast + 0.05)

if __name__ == '__main__':
    unittest.main()
