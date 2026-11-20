"""Checks Part 2's model: the nested time to capacity matches R tau_pod + (R - m) tau_node within
the scan and sync latencies when headroom covers exactly m rounds, a node loop that sees the
final need does no worse than one that sees only pending pods, and headroom covering every
round removes every node wait. Headroom between thresholds is reported, not tested: its effect
is not monotone (T8).

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import covered_rounds, headroom_for, nested_time, rounds, separated_time
from nested import simulate

LATENCY = 15 + 10 + 5   # one sync period, one scan interval and one time step, per round


class NestedLoops(unittest.TestCase):

    def test_nested_time_matches_the_closed_form(self):
        for k in (3, 5, 10, 30, 100):
            for tau_node in (30, 120, 210, 600):
                sim = simulate(k, tau_node=tau_node)
                closed = nested_time(k, 90, tau_node)
                self.assertGreaterEqual(sim, closed)
                self.assertLessEqual(sim, closed + rounds(k) * LATENCY)

    def test_without_node_rounding_the_bound_holds_at_every_target(self):
        """With one pod per node no slot is ever left over, so every round waits for nodes."""
        for target in (0.4, 0.5, 0.6, 0.7):
            sim = simulate(30, target=target, per_node=1)
            closed = nested_time(30, 90, 210, target=target)
            self.assertGreaterEqual(sim, closed)
            self.assertLessEqual(sim, closed + rounds(30, target=target) * LATENCY)

    def test_node_rounding_can_cover_small_rounds(self):
        self.assertLess(simulate(30, target=0.7, per_node=8), nested_time(30, 90, 210, target=0.7))

    def test_separated_time_matches_the_closed_form(self):
        for k in (5, 10, 30, 100):
            for tau_node in (30, 210, 600):
                sim = simulate(k, tau_node=tau_node, oracle=True)
                closed = separated_time(k, 90, tau_node)
                self.assertGreaterEqual(sim, closed)
                self.assertLessEqual(sim, closed + rounds(k) * LATENCY)

    def test_seeing_the_final_need_never_hurts(self):
        for k in (3, 10, 30):
            for headroom in (0, 16, 48):
                ample = simulate(k, headroom=10 ** 6)
                separated = simulate(k, headroom=headroom, oracle=True)
                nested = simulate(k, headroom=headroom)
                self.assertLessEqual(ample, separated)
                self.assertLessEqual(separated, nested)

    def test_headroom_thresholds_count_whole_rounds(self):
        """covered_rounds steps exactly at n0 (g^m - 1) slots, one round per step."""
        n0 = 16
        for m in range(rounds(30)):
            self.assertEqual(covered_rounds(int(headroom_for(m, n0, 30)), n0, 30), m)
            self.assertEqual(covered_rounds(int(headroom_for(m + 1, n0, 30)) - 1, n0, 30), m)

    def test_full_headroom_removes_every_node_wait(self):
        for k in (5, 10, 30):
            self.assertEqual(simulate(k, headroom=10 ** 6), simulate(k, headroom=int(headroom_for(rounds(k), 16, k))))

    def test_covered_headroom_matches_the_closed_form(self):
        n0 = 16
        for m in range(rounds(30) + 1):
            h = int(headroom_for(m, n0, 30))
            sim = simulate(30, headroom=h)
            closed = nested_time(30, 90, 210, m=covered_rounds(h, n0, 30))
            self.assertGreaterEqual(sim, closed)
            self.assertLessEqual(sim, closed + rounds(30) * LATENCY)


class LoadMetric(unittest.TestCase):

    def test_a_load_metric_sizes_the_surge_without_waiting_for_ready_pods(self):
        # Desired replicas follow total load over the per-pod target, so only the default scale-up
        # policy paces the requests (doubling every 15 s) and the surge pays one node wait.
        t = simulate(30, metric="load")
        self.assertGreaterEqual(t, 90 + 210)
        self.assertLessEqual(t, 60 + 210 + 90 + 15 + 10)
        self.assertLess(t, simulate(30))

    def test_utilization_metric_unchanged(self):
        self.assertEqual(simulate(30, metric="utilization"), simulate(30))


if __name__ == '__main__':
    unittest.main()
