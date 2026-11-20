"""Checks Part 6's seam ratios: for each seam, what the composite asks over what it can give, so that the seam
binds when the ratio passes one. Signal: the step factor 1/((1+m) q u_h) over 1 + tol_up, which passes one
exactly below the band of Proposition 3 (steady load). Time scale: the rounds a surge needs over the rounds
the headroom covers plus one, which passes one exactly when nesting costs a node wait (Proposition 9).
State: the forced backlog over the mean watch plus the history, Proposition 21's necessary condition.
Order: the passes an order needs over the passes allowed (Proposition 37). Assumption: the spectral radius of
the start-time graph, zero without a cycle, one with cycles that share no component, above one where cycles
interlock, and close to Proposition 26's E[k_in k_out] / E[k] in a large random graph above its threshold. A test scaled to a fraction f of the nodes, keeping every
mechanism, keeps every ratio but the state's, which falls by f for informers whose list does not grow with
the cluster and by f^2 for informers whose list does.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import random
import unittest

import hpa_vpa
import nested
import relist
from formulas import equilibrium_band, rounds
from percolation import gen_needs
from ratios import assumption_ratio, order_ratio, scaled_state_ratio, signal_ratio, state_ratio, time_ratio


class Ratios(unittest.TestCase):

    def test_signal_passes_one_exactly_below_the_band(self):
        lo = equilibrium_band(q=1.0)[0]
        self.assertGreater(signal_ratio(lo - 0.001), 1.0)
        self.assertLessEqual(signal_ratio(lo + 0.001), 1.0)
        self.assertAlmostEqual(signal_ratio(0.5), 1.0 / (1.15 * 0.5 * 1.1))

    def test_signal_passes_one_above_the_band_too(self):
        hi = equilibrium_band(q=1.0)[1]
        self.assertGreater(signal_ratio(hi + 0.001), 1.0)
        self.assertLessEqual(signal_ratio(hi - 0.001), 1.0)

    def test_assumption_radius(self):
        self.assertEqual(assumption_ratio({'a': {'b'}, 'b': {'c'}, 'c': set()}), 0.0)
        self.assertAlmostEqual(assumption_ratio({'a': {'b'}, 'b': {'c'}, 'c': {'a'}, 'd': {'a'}}), 1.0, places=6)
        self.assertAlmostEqual(assumption_ratio({'a': {'b', 'c'}, 'b': {'a'}, 'c': {'a'}}), 2 ** 0.5, places=6)

    def test_assumption_radius_matches_the_threshold_law(self):
        for c in (2.0, 3.0):
            needs = gen_needs(c, [1.0] * 2000, random.Random(1))
            edges = sum(len(v) for v in needs.values()) / 2000.0
            self.assertAlmostEqual(assumption_ratio(needs) / edges, 1.0, delta=0.05)

    def test_time_passes_one_when_nesting_costs(self):
        self.assertEqual(rounds(30), 4)
        self.assertAlmostEqual(time_ratio(30, covered=0), 4.0)
        self.assertLessEqual(time_ratio(3, covered=0), 1.0)          # one round: nothing to nest
        self.assertLessEqual(time_ratio(30, covered=3), 1.0)         # three rounds covered, the fourth waits once

    def test_state(self):
        self.assertAlmostEqual(state_ratio(2000, 100.0, 100.0, 450.0, 300.0), 2000.0 / 750.0)

    def test_order(self):
        self.assertAlmostEqual(order_ratio(3, 2), 1.5)

    def test_scaled_state(self):
        self.assertAlmostEqual(scaled_state_ratio(3.0, 0.5, grows=False), 1.5)
        self.assertAlmostEqual(scaled_state_ratio(3.0, 0.5, grows=True), 0.75)



class ScaledTests(unittest.TestCase):
    """A test cluster at a tenth of the scale keeps the verdicts whose ratios do not depend on scale, and keeps
    the shared state's only at a tenth of the capacity."""

    def test_signal_keeps_its_doubling(self):
        full = hpa_vpa.simulate(0.5, demand=100.0, replicas=10, days=40)[1]
        tenth = hpa_vpa.simulate(0.5, demand=10.0, replicas=1, days=40)[1]
        self.assertAlmostEqual(tenth / full, 1.0, delta=0.02)

    def test_time_keeps_its_rounds_with_headroom_in_proportion(self):
        self.assertEqual(nested.simulate(30, n0=16), nested.simulate(30, n0=160))
        self.assertEqual(nested.simulate(30, n0=16, headroom=16), nested.simulate(30, n0=160, headroom=160))
        self.assertGreater(nested.simulate(30, n0=160, headroom=16), nested.simulate(30, n0=160, headroom=160))

    def test_state_needs_the_capacity_scaled(self):
        full = relist.simulate_limited(120.0, clients=2000, capacity=100.0, hours=4)[0]
        same = relist.simulate_limited(120.0, clients=200, capacity=100.0, hours=4)[0]
        tenth = relist.simulate_limited(120.0, clients=200, capacity=10.0, hours=4)[0]
        self.assertEqual(same[1:], [0, 0, 0])
        for a, b in zip(full[1:], tenth[1:]):
            self.assertAlmostEqual(b / a, 0.1, delta=0.01)

    def test_state_with_growing_lists_needs_the_square(self):
        tenth = relist.simulate_limited(12.0, clients=200, capacity=1.0, hours=4)[0]
        self.assertGreater(min(tenth[1:]), 250)


if __name__ == '__main__':
    unittest.main()
