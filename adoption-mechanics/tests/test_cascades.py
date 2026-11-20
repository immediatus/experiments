"""Checks the aggregation stage's cascades: with binary signals of bounded precision, a public lead of two
locks every later member into the herd whatever their own signal, and a member who values revealing their
signal to later members (the observed-player effect) needs a longer lead, which lowers the share of runs
that end in a wrong cascade.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from cascades import cascade_share, public_lead, sequence


class Cascades(unittest.TestCase):

    def test_lock_in_after_lead_of_two(self):
        acts = sequence([-1, -1, +1, +1, +1], precision=0.7)
        self.assertEqual(acts, [-1, -1, -1, -1, -1])

    def test_no_lock_in_without_a_lead(self):
        self.assertEqual(sequence([+1, -1, +1, -1], precision=0.7), [+1, -1, +1, -1])

    def test_probing_needs_a_longer_lead(self):
        acts = sequence([-1, -1, +1, +1, +1], precision=0.7, probe_weight=1.0)
        self.assertEqual(acts[:3], [-1, -1, +1])

    def test_probing_reduces_wrong_cascades(self):
        a = cascade_share(30, 0.7, 0.0, trials=20000, seed=1)
        b = cascade_share(30, 0.7, 1.0, trials=20000, seed=1)
        self.assertGreater(a, 0.05)
        self.assertLess(b, a)


class CorrelatedPeers(unittest.TestCase):

    def test_correlation_raises_wrong_cascades(self):
        a = cascade_share(30, 0.7, 0.0, trials=20000, seed=1, rho=0.0)
        b = cascade_share(30, 0.7, 0.0, trials=20000, seed=1, rho=0.6)
        self.assertGreater(b, a + 0.05)

    def test_rho_zero_matches_independent_closed_form(self):
        q = 0.7
        self.assertAlmostEqual(cascade_share(30, q, 0.0, trials=40000, seed=8, rho=0.0),
                               (1 - q) ** 2 / (1 - 2 * q * (1 - q)), delta=0.01)



class AsymmetricWeights(unittest.TestCase):

    def test_weight_against_delays_lock_in_against(self):
        signals = [-1, -1, 1, 1, 1]
        self.assertEqual(sequence(signals, 0.7), [-1, -1, -1, -1, -1])
        self.assertEqual(sequence(signals, 0.7, probe_weight=0.0, probe_against=5.0), signals)

    def test_weight_against_defaults_to_weight_for(self):
        signals = [-1, -1, -1, 1, 1, 1, 1]
        self.assertEqual(sequence(signals, 0.7, 1.0), sequence(signals, 0.7, 1.0, probe_against=1.0))


class PublicLead(unittest.TestCase):

    def test_lead_stops_growing_once_locked(self):
        self.assertEqual(public_lead([1, 1, -1, -1, -1], 0.7), 2)

    def test_lead_counts_revealed_signals_before_lock(self):
        self.assertEqual(public_lead([1, -1, -1], 0.7), -1)

if __name__ == '__main__':
    unittest.main()
