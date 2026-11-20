"""Checks the backlog loop: the idealized loop of backlog_ideal decays below its critical gain and grows above
it, and its growth does not depend on the size of the perturbation (the filter is positively homogeneous); the
deployed loop of backlog_sim rests at its equilibrium without a step and is reproducible for a seed; and the
boundary of backlog_boundary separates hunting from settling.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from backlog_boundary import boundary, hunts, phi
from backlog_ideal import critical_a, growth, step_response
from backlog_sim import run


class IdealLoop(unittest.TestCase):

    def test_decays_below_the_critical_gain_and_grows_above(self):
        a = critical_a(0.5, cycles_time=100.0)
        self.assertLess(growth(0.5 * a, 0.5, cycles_time=100.0), 1.0)
        self.assertGreater(growth(2.0 * a, 0.5, cycles_time=100.0), 1.0)

    def test_growth_does_not_depend_on_the_perturbation_size(self):
        a = critical_a(0.5, cycles_time=100.0)
        for gain in (0.5 * a, 0.9 * a):
            small = growth(gain, 0.5, cycles_time=100.0, start=-1.0)
            large = growth(gain, 0.5, cycles_time=100.0, start=-7.0)
            self.assertAlmostEqual(small, large, delta=1e-9 * max(1.0, small))

    def test_step_response_without_a_window_never_overshoots(self):
        top, falls = step_response(0.2, 0.0, steps=5000)
        self.assertEqual(top, 0.0)
        self.assertEqual(falls, 0)

    def test_boundary_function_is_the_reciprocal_of_the_critical_gain(self):
        self.assertAlmostEqual(phi(0.5) * critical_a(0.5), 1.0, places=12)


class DeployedLoop(unittest.TestCase):

    def test_rests_at_equilibrium_without_a_step(self):
        o = run(50, lam0=200.0, lam1=200.0, horizon=7200)
        self.assertEqual((o['n_lo'], o['n_hi'], o['flips']), (o['need'], o['need'], 0))

    def test_a_short_standing_delay_hunts_and_a_long_one_settles(self):
        self.assertTrue(hunts(5, 90, 300)[0])
        self.assertFalse(hunts(500, 90, 300)[0])

    def test_boundary_lies_between_a_hunting_and_a_settled_delay(self):
        b = boundary(90, 300)
        self.assertTrue(5 < b < 500)
        self.assertTrue(hunts(b - 2.0, 90, 300)[0])
        self.assertFalse(hunts(b + 2.0, 90, 300)[0])

    def test_noise_is_reproducible_for_a_seed(self):
        a = run(400, noise=0.3, seed=3, horizon=7200)
        self.assertEqual(a, run(400, noise=0.3, seed=3, horizon=7200))
        self.assertNotEqual(a, run(400, noise=0.3, seed=4, horizon=7200))

    def test_trace_holds_every_second(self):
        trace = []
        run(400, horizon=3700, trace=trace)
        self.assertEqual(len(trace), 3700)


if __name__ == '__main__':
    unittest.main()
