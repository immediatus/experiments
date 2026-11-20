"""Checks the career plane: the directions the literature fixes for whether a member voices a signal against
the consensus. Uncertain juniors herd (Scharfstein and Stein 1990); members confident of their own ability
contradict the consensus (Avery and Chevalier 1999); members who endorsed the incumbent defend it
(Prendergast and Stole 1996); with no horizon, reputation drops out but immediate conformity does not.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from career import speaks, voice_margin


class Plane(unittest.TestCase):

    def test_uncertain_junior_stays_silent(self):
        self.assertFalse(speaks(True, kappa=0.1, endorsed_incumbent=False, delta=0.7, gamma=0.6))

    def test_confident_senior_contradicts(self):
        self.assertTrue(speaks(True, kappa=0.9, endorsed_incumbent=False, delta=0.9, gamma=0.15))

    def test_incumbent_author_defends(self):
        self.assertFalse(speaks(True, kappa=0.9, endorsed_incumbent=True, delta=0.9, gamma=0.15))

    def test_zero_horizon_removes_reputation_but_not_conformity(self):
        self.assertFalse(speaks(True, kappa=0.1, endorsed_incumbent=False, delta=0.0, gamma=0.9))
        self.assertTrue(speaks(True, kappa=0.1, endorsed_incumbent=False, delta=0.0, gamma=0.0))

    def test_agreeing_with_consensus_is_always_voiced(self):
        self.assertTrue(speaks(False, kappa=0.1, endorsed_incumbent=True, delta=0.9, gamma=0.9))


class Direction(unittest.TestCase):

    def test_endorser_defends_incumbent(self):
        toward = voice_margin(0.9, True, 0.9, 0.15, toward_successor=True)
        against = voice_margin(0.9, True, 0.9, 0.15, toward_successor=False)
        self.assertLess(toward, 0.0)
        self.assertGreater(against, voice_margin(0.9, False, 0.9, 0.15))

    def test_no_endorsement_direction_free(self):
        self.assertAlmostEqual(voice_margin(0.5, False, 0.9, 0.15, toward_successor=True),
                               voice_margin(0.5, False, 0.9, 0.15, toward_successor=False))


if __name__ == '__main__':
    unittest.main()
