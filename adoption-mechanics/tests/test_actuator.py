"""Checks the actuator stage. Vetoes: with Euclidean preferences the set of changes every veto player prefers
to the status quo is empty exactly when the status quo lies in the convex hull of their ideal points
(Tsebelis 1995); an ideal point inside the hull changes nothing (absorption). Hysteresis: with no sunk cost
the adopt and abandon thresholds coincide, and the band between them widens with the cost.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import math
import random
import unittest

from actuator import amend_to_win_set, band_exponent, hysteresis_band, in_hull, setter_proposal, win_set_nonempty

TRIANGLE = [(-1.0, -1.0), (1.0, -1.0), (0.0, 1.0)]


def _sq_dist(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


class Vetoes(unittest.TestCase):

    def test_cliff_inside_hull(self):
        self.assertFalse(win_set_nonempty((0.0, 0.0), TRIANGLE))

    def test_cliff_on_hull_edge(self):
        self.assertFalse(win_set_nonempty((0.0, -1.0), TRIANGLE))

    def test_open_outside_hull(self):
        self.assertTrue(win_set_nonempty((3.0, 0.0), TRIANGLE))

    def test_absorption(self):
        for sq in [(3.0, 0.0), (0.0, 0.0), (0.5, 2.0)]:
            self.assertEqual(win_set_nonempty(sq, TRIANGLE), win_set_nonempty(sq, TRIANGLE + [(0.0, -0.2)]))

    def test_in_hull_single_and_pair(self):
        self.assertTrue(in_hull((1.0, 1.0), [(1.0, 1.0)]))
        self.assertTrue(in_hull((0.5, 0.5), [(0.0, 0.0), (1.0, 1.0)]))
        self.assertFalse(in_hull((0.5, 0.6), [(0.0, 0.0), (1.0, 1.0)]))

    def test_monte_carlo_agrees(self):
        rng = random.Random(11)
        for _ in range(50):
            ideals = [(rng.uniform(-2, 2), rng.uniform(-2, 2)) for _ in range(rng.choice([2, 3, 4]))]
            sq = (rng.uniform(-3, 3), rng.uniform(-3, 3))
            found = False
            for _ in range(2000):
                x = (rng.uniform(-4, 4), rng.uniform(-4, 4))
                if all(_sq_dist(x, z) < _sq_dist(sq, z) for z in ideals):
                    found = True
                    break
            if found:
                self.assertTrue(win_set_nonempty(sq, ideals))
            if not win_set_nonempty(sq, ideals):
                self.assertFalse(found)


class AgendaSetter(unittest.TestCase):
    GATES = [(2.0, 0.5), (1.5, -0.5), (2.5, -0.2), (2.2, 0.8)]

    def test_proposal_beats_or_ties_the_status_quo_for_every_gate(self):
        sq = (1.0, 0.0)
        for k in range(4):
            x = setter_proposal(sq, self.GATES, k)
            for z in self.GATES:
                self.assertLessEqual(math.dist(x, z), math.dist(sq, z) + 1e-9)

    def test_proposal_lands_in_the_hull_and_ends_change(self):
        for sq in ((1.0, 0.0), (0.0, 0.0), (3.5, 0.0)):
            for k in range(4):
                x = setter_proposal(sq, self.GATES, k)
                self.assertTrue(in_hull(x, self.GATES, eps=1e-7), (sq, k, x))

    def test_no_point_of_the_win_set_is_closer_to_the_setter(self):
        sq, k = (1.0, 0.0), 2
        x = setter_proposal(sq, self.GATES, k)
        radii = [math.dist(sq, z) for z in self.GATES]
        for i in range(200):
            for j in range(1, 100):
                a, r = 2 * math.pi * i / 200, 1.6 * j / 100
                p = (sq[0] + r * math.cos(a), sq[1] + r * math.sin(a))
                if all(math.dist(p, z) < rz for z, rz in zip(self.GATES, radii)):
                    self.assertGreaterEqual(math.dist(p, self.GATES[k]), math.dist(x, self.GATES[k]) - 1e-9)

    def test_setter_whose_ideal_is_acceptable_gets_it(self):
        gates = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        x = setter_proposal((5.0, 5.0), gates, 2)
        self.assertAlmostEqual(x[0], 0.5, places=9)
        self.assertAlmostEqual(x[1], 1.0, places=9)


class Amendment(unittest.TestCase):
    """The change nearest a design that every gate strictly prefers to the status quo."""

    SQ = (0.0, 0.0)

    def _passes(self, d, gates):
        return all((d[0] - z[0]) ** 2 + (d[1] - z[1]) ** 2 < (self.SQ[0] - z[0]) ** 2 + (self.SQ[1] - z[1]) ** 2
                   for z in gates)

    def test_a_design_that_passes_is_kept(self):
        gates = [(2.0, 0.5), (1.5, -0.5), (2.5, -0.2), (2.2, 0.8)]
        self.assertEqual(amend_to_win_set((1.8, 0.1), self.SQ, gates), (1.8, 0.1))

    def test_the_amendment_passes_every_gate(self):
        rng = random.Random(3)
        for _ in range(40):
            gates = [(rng.uniform(0.5, 3), rng.uniform(-1, 1)) for _ in range(5)]
            if not win_set_nonempty(self.SQ, gates):
                continue
            self.assertTrue(self._passes(amend_to_win_set((3.0, 2.0), self.SQ, gates), gates))

    def test_no_passing_point_on_a_grid_is_nearer(self):
        gates = [(2.0, 0.5), (1.5, -0.5), (0.6, 1.4)]
        d = (2.5, -1.5)
        a = amend_to_win_set(d, self.SQ, gates)
        best = math.hypot(a[0] - d[0], a[1] - d[1])
        for i in range(-60, 61):
            for j in range(-60, 61):
                q = (i / 20.0, j / 20.0)
                if self._passes(q, gates):
                    self.assertGreaterEqual(math.hypot(q[0] - d[0], q[1] - d[1]), best - 1e-6)

    def test_an_empty_win_set_is_rejected(self):
        with self.assertRaises(ValueError):
            amend_to_win_set((1.0, 0.0), (1.0, 0.0), [(2.0, 0.0), (0.0, 1.0), (0.0, -1.0)])


class Hysteresis(unittest.TestCase):

    def test_band_zero_without_sunk_cost(self):
        lo, hi = hysteresis_band(0.0, 1.0, 1.0, 0.95)
        self.assertAlmostEqual(hi - lo, 0.0, delta=1e-6)

    def test_band_widens_with_cost(self):
        widths = [hi - lo for lo, hi in (hysteresis_band(c, 1.0, 1.0, 0.95) for c in (0.05, 0.2, 0.8))]
        self.assertTrue(widths[0] < widths[1] < widths[2])

    def test_exponent_is_positive_and_below_one(self):
        e = band_exponent([0.05, 0.1, 0.2, 0.4], loss_aversion=1.0, sigma=1.0, discount=0.95)
        self.assertTrue(0.0 < e < 1.0)


class LossOnSwitch(unittest.TestCase):

    def test_loss_on_switch_raises_adoption(self):
        flow = hysteresis_band(0.2, 2.25, 1.0, 0.95, tol=1e-7)
        switch = hysteresis_band(0.2, 2.25, 1.0, 0.95, tol=1e-7, loss_on='switch')
        plain = hysteresis_band(0.2, 1.0, 1.0, 0.95, tol=1e-7, loss_on='switch')
        self.assertGreater(switch[1], plain[1] + 0.05)
        self.assertGreater(switch[1], flow[1] + 0.05)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            hysteresis_band(0.2, 2.25, 1.0, 0.95, loss_on='nowhere')


if __name__ == '__main__':
    unittest.main()
