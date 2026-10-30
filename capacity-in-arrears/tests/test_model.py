"""Checks the simulations against properties they must have whatever their inputs: work is
conserved, a metric that cannot saturate sizes a step in one go, the closed forms agree with the
fluid model, and the request-level simulator is deterministic for a seed. The byte-for-byte
check of reproduce.py says the numbers did not change; these say the model is right.

Run: python3 tests/test_model.py   or   python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), p) for p in [os.path.join('..', 'model')]]

import math
import unittest

from backlog_ideal import step_response
from formulas import hottest_target, recovery_long_spike, recovery_piecewise, rounds, stale_gain_bound
from hpa_port import Normalizer
from loop_sim import pods_needed, run, step
from request_sim import simulate


class WorkConservation(unittest.TestCase):
    """With abandoned work served (the default), every unit that arrives ends up served for a
    waiting client, served after its client left, refused at the door, or still queued, either
    for its client or as abandoned work."""

    CASES = [
        ('no timeouts', dict()),
        ('timeouts and retries', dict(timeout=10, retries=2)),
        ('admission bound', dict(timeout=10, retries=2, shed_s=5)),
        ('retry budget', dict(timeout=10, retries=5, budget=0.2)),
        ('backoff', dict(timeout=10, retries=2, backoff=5)),
    ]

    def test_arrivals_equal_outcomes(self):
        for name, kw in self.CASES:
            with self.subTest(name):
                series = []
                o = run(step(10, until=360), 'cpu', horizon=4000, series=series, **kw)
                arrived = math.fsum(row[3] for row in series)
                _, _, _, _, _, _, queued, abandoned = series[-1]
                accounted = math.fsum([o['good'], o['wasted'], o['rejected'], queued, abandoned])
                self.assertAlmostEqual(arrived, accounted, delta=1e-6 * arrived)

    def test_dropped_abandoned_work_is_not_served(self):
        o = run(step(10, until=360), 'cpu', horizon=4000, timeout=10, retries=2, zombie=False)
        self.assertEqual(o['wasted'], 0.0)


class Sizing(unittest.TestCase):

    def test_a_metric_that_cannot_saturate_sizes_a_step_exactly(self):
        # Part 1: with the limit far above the request the controller sees the load and stops at the need
        for k in (2, 10, 30):
            with self.subTest(k=k):
                o = run(step(k), 'cpu', limit=100.0, horizon=3600)
                self.assertEqual(o['peak'], pods_needed(o, k))

    def test_a_saturated_metric_overshoots(self):
        o = run(step(10), 'cpu', horizon=3600)
        self.assertGreater(o['peak'], pods_needed(o, 10))

    def test_scales_follow_the_inputs(self):
        o = run(step(5), 'cpu', n0=4, target=25, horizon=600)
        self.assertEqual((o['base'], o['per_pod']), (100.0, 25.0))
        self.assertEqual(pods_needed(o, 5), 20)


class ClosedForms(unittest.TestCase):

    def test_rounds_and_hottest_target_match_the_posts(self):
        self.assertEqual(rounds(30), 4)                 # 30x at a 50% target
        self.assertEqual(rounds(30, target=80), 15)     # and at the API default
        self.assertEqual(rounds(1.5), 0)                # within one pod's headroom
        self.assertEqual(hottest_target(10, 4), 63)     # Corollary 2, tenfold within four rounds

    def test_stale_gain_bound(self):
        self.assertAlmostEqual(stale_gain_bound(0), 2.0)
        self.assertAlmostEqual(stale_gain_bound(1), 1.0)   # the one-line rule is marginal at d = 1
        self.assertLess(stale_gain_bound(2), 1.0)          # and unstable from d = 2

    def test_recovery_forms(self):
        self.assertIsNone(recovery_long_spike(10, 0.5, 2, 300))
        self.assertIsNone(recovery_piecewise(10, 0.5, 2, 300, 10))
        # the long-spike form is the limit of the full form
        long_spike = 10 ** 6
        ratio = recovery_piecewise(10, 0.25, 2, long_spike, 10) / recovery_long_spike(10, 0.25, 2, long_spike)
        self.assertAlmostEqual(ratio, 1.0, places=4)

    def test_full_form_matches_the_fluid_model(self):
        # Proposition 7 against the fluid model, at fixed capacity (Part 3)
        for k, rho, retries in ((10, 0.5, 0), (10, 0.25, 1), (5, 0.25, 2)):
            with self.subTest(k=k, rho=rho, retries=retries):
                n0 = 10 if k == 10 else 4
                o = run(step(k, until=360), 'cpu', target=round(rho * 100), n0=n0, max_replicas=n0,
                        timeout=10, retries=retries, horizon=8000)
                predicted = recovery_piecewise(k, rho, retries + 1, 300, 10)
                self.assertLess(abs(o['last_bad'] - 360 - predicted) / predicted, 0.012)

    def test_window_proof_delay(self):
        # Proposition 5: at a standing delay of e dead times no window acts and nothing overshoots
        for w in (1, 10, 100):
            with self.subTest(w=w):
                self.assertEqual(step_response(1 / math.e, w), (0.0, 0))


class Normalization(unittest.TestCase):
    """The default-path normalization of horizontal.go: scale-up limit, then the downscale window."""

    def test_scale_up_limit(self):
        self.assertEqual(Normalizer()(0, 10, 100), 20)   # at most double
        self.assertEqual(Normalizer()(0, 1, 100), 4)     # or four, whichever is more

    def test_downscale_window_holds_the_highest_recommendation(self):
        n = Normalizer()
        self.assertEqual(n(0, 10, 20), 20)
        self.assertEqual(n(15, 20, 5), 20)               # held: 20 was recommended within 300 s
        self.assertEqual(n(316, 20, 5), 5)               # released once it leaves the window


class RequestLevel(unittest.TestCase):

    def test_deterministic_for_a_seed(self):
        a = simulate(0.5, 0, 1, horizon=3000.0)
        self.assertEqual(a, simulate(0.5, 0, 1, horizon=3000.0))
        self.assertNotEqual(a, simulate(0.5, 0, 2, horizon=3000.0))


if __name__ == '__main__':
    unittest.main()
