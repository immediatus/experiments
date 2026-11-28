"""Checks the pod-memory extension of Part 2's model. A memory of M seconds after a surge can be
kept by the pod loop's stabilization window, the node loop's unneeded time, or both; the spare
nodes are held for min(G, M) either way, so the split does not change the node-time held, and
putting all of it in the pod loop serves every gap shorter than M at once. With memoryless gaps the
pod-memory settings trace a straight line below the node-memory curve, and holding pods for the
break-even time is a plain rent-or-buy rule, at most twice the hindsight cost for every gap.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import WINDOW_CAP, expected_held, expected_time, memory_cost, memory_split, nested_time, pod_break_even, pod_worst_ratio, second_surge_time
from nested import simulate_two_surges

SPARE, S, POD, NODE, K = 58, 300, 90, 210, 30
LATENCY = 15 + 10 + 5


class PodMemory(unittest.TestCase):
    """Moving memory into the pod loop never hurts; simulation holds the same nodes and serves no later; memoryless
    pod line lies below the node curve; pod break even is at most twice the hindsight cost; a memory fills the pod
    window first up to its cap; capped memoryless optimum is one of three settings."""

    def test_moving_memory_into_the_pod_loop_never_hurts(self):
        for m in (600, 900, 1500):
            for gap in range(0, 2400, 15):
                nodes = second_surge_time(gap, K, POD, NODE, S, m - S)
                pods = second_surge_time(gap, K, POD, NODE, m, 0)
                self.assertLessEqual(pods, nodes, (m, gap))
                if S <= gap < m:
                    self.assertLess(pods, nodes, (m, gap))
                self.assertEqual(pods, 0 if gap < m else nested_time(K, POD, NODE))

    def test_simulation_holds_the_same_nodes_and_serves_no_later(self):
        for gap in (150, 450, 700, 850, 1200):
            nt, nh = simulate_two_surges(gap, stabilization=S, unneeded=600, bulk=10 ** 6)
            pt, ph = simulate_two_surges(gap, stabilization=900, unneeded=0, bulk=10 ** 6)
            self.assertLessEqual(pt, nt + LATENCY, gap)
            self.assertAlmostEqual(ph, nh, delta=SPARE * 30, msg=gap)
            if gap < 900:
                self.assertEqual(pt, 0, gap)

    def test_memoryless_pod_line_lies_below_the_node_curve(self):
        cold = nested_time(K, POD, NODE)
        for mu in (600, 1800, 7200):
            for u in (0, 300, 600, 1200, 3600):
                w = expected_held(u, mu, SPARE, S)
                pod_time = cold * (1 - w / (SPARE * mu))
                self.assertAlmostEqual(pod_time, expected_time(0, mu, K, POD, NODE, S + u), places=6)
                if u:   # at u = 0 the two are the same setting
                    self.assertLess(pod_time, expected_time(u, mu, K, POD, NODE, S), (mu, u))

    def test_pod_break_even_is_at_most_twice_the_hindsight_cost(self):
        for lam in (4, 16, 64, 160):
            b = pod_break_even(lam, K, POD, NODE, SPARE)
            self.assertLessEqual(b, WINDOW_CAP)
            self.assertAlmostEqual(b, lam * nested_time(K, POD, NODE) / SPARE)
            self.assertLessEqual(pod_worst_ratio(b, lam, K, POD, NODE, SPARE), 2 + 1e-9)


    def test_a_memory_fills_the_pod_window_first_up_to_its_cap(self):
        self.assertEqual(WINDOW_CAP, 3600)
        self.assertEqual(memory_split(900), (900, 0))
        self.assertEqual(memory_split(5000), (3600, 1400))

    def test_capped_memoryless_optimum_is_one_of_three_settings(self):
        ends = (0, WINDOW_CAP, 10 ** 9)
        for mu in (600, 1800, 7200):
            lo = SPARE * mu / nested_time(K, POD, NODE)
            hi = SPARE * mu / (4 * NODE)
            for lam in (lo * 0.9, lo * 1.1, (lo + hi) / 2, hi * 0.95, hi * 1.05, hi * 3):
                def cost(m):
                    return memory_cost(m, mu, lam, K, POD, NODE, SPARE)
                best_end = min(ends, key=cost)
                for m in range(30, 20001, 30):
                    self.assertGreaterEqual(cost(m), cost(best_end) - 1e-6, (mu, lam, m))
                expect = 0 if lam < lo else WINDOW_CAP if lam < hi else 10 ** 9
                self.assertEqual(best_end, expect, (mu, lam))


if __name__ == '__main__':
    unittest.main()
