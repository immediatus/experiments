"""Checks Part 3's mixed informers: a list cost given per client reproduces the single-cost runs when
every client has the same cost, under one queue and under fair queuing, and the per-client counts of
re-watches answered 410 add up to the total.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from relist import simulate_fair, simulate_limited


class Mixed(unittest.TestCase):
    """Uniform costs reproduce the scalar run; per client counts add up."""

    def test_uniform_costs_reproduce_the_scalar_run(self):
        for sim in (simulate_limited, simulate_fair):
            a = sim(100.0, clients=300, capacity=15.0, hours=3)
            b = sim([100.0] * 300, clients=300, capacity=15.0, hours=3)
            self.assertEqual(a[:5], b[:5])

    def test_per_client_counts_add_up(self):
        for sim in (simulate_limited, simulate_fair):
            out = sim([20.0] * 250 + [400.0] * 50, clients=300, capacity=15.0, hours=3)
            self.assertEqual(sum(out[-1]['gone']), out[1])
            self.assertEqual(len(out[-1]['lists']), 300)


class LastGone(unittest.TestCase):
    """Last 410 time is recorded."""

    def test_last_410_time_is_recorded(self):
        out = simulate_limited(40.0, hours=3)
        self.assertEqual(out[1] > 0, out[-1]['last_gone'] > 0)
        self.assertLess(out[-1]['last_gone'], 3 * 3600.0)
        self.assertEqual(simulate_limited(10.0, hours=2)[-1]['last_gone'], 0.0)


class EqualWork(unittest.TestCase):
    """Mixed sizes storm at the same total work."""

    def test_mixed_sizes_storm_at_the_same_total_work(self):
        def mix(c, ratio, small=1900, large=100):
            cs = 2000 * c / (small + large * ratio)
            return [cs] * small + [cs * ratio] * large
        self.assertGreater(simulate_limited(mix(113.0, 20.0))[0][-1], 0)
        self.assertEqual(simulate_limited(mix(112.0, 20.0))[0][-1], 0)


if __name__ == '__main__':
    unittest.main()
