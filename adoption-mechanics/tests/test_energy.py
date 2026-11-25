"""Checks the human energy budget of a review: Part 1's meeting, where every pair of opinion holders on a piece
settles its disagreement (a mesh, quadratic in the holders), against the unrouted Residual Protocol, where only departures
from the machines' reference are settled (a star, linear in the departures), and against the machine heard first,
which spends no human energy and decides by the reference alone. The meeting must reproduce Part 1's law of
triviality; the protocol's numbers are checked against a case worked by hand.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from energy import expected_settlements, review_energy
from pipeline import bikeshed, settle_in_time, window_survival


class Settlement(unittest.TestCase):

    def test_settle_in_time_matches_the_window_of_part_one(self):
        for groups in (2, 3, 6):
            self.assertAlmostEqual(settle_in_time(groups * (groups - 1) // 2, 13.0, 1.0),
                                   window_survival(groups, 13.0, 1.0), places=12)

    def test_no_settlement_always_fits(self):
        self.assertEqual(settle_in_time(0, 13.0, 0.25), 1.0)

    def test_mesh_is_quadratic_and_star_linear(self):
        self.assertAlmostEqual(expected_settlements(15, 0.95), 105 * 0.95 ** 2, places=12)
        self.assertAlmostEqual(expected_settlements(15, 0.95, depart=0.1), 15 * 0.95 * 0.1, places=12)


class Meeting(unittest.TestCase):

    def test_reproduces_the_law_of_triviality(self):
        for pieces in (1, 2, 4):
            exact = review_energy(pieces, 'meeting', True)['adopted']
            self.assertAlmostEqual(exact, bikeshed(pieces, 20000, 1)[2], delta=0.01)

    def test_settlements_are_the_mesh(self):
        for pieces in (1, 4):
            share = min(0.95, 0.2 * pieces ** 0.75)
            out = review_energy(pieces, 'meeting', True)
            self.assertAlmostEqual(out['settlements'], pieces * expected_settlements(15, share), places=9)
            self.assertAlmostEqual(out['weeks'], out['settlements'] * 0.25, places=9)


class Residual(unittest.TestCase):

    def test_a_case_worked_by_hand(self):
        # one reviewer, one piece: holds an opinion with chance 0.2; accepts with chance 0.9; an objection is one
        # departure, settled within the window with chance W1, and resolved to the truth (accept) with chance 0.9
        w1 = settle_in_time(1, 13.0, 0.25)
        expected = 0.8 + 0.2 * (0.9 + 0.1 * w1 * 0.9)
        self.assertAlmostEqual(review_energy(1, 'residual', True, reviewers=1)['adopted'], expected, places=12)

    def test_spends_less_than_the_meeting(self):
        for pieces in (1, 2, 4, 8):
            self.assertLess(review_energy(pieces, 'residual', True)['settlements'],
                            review_energy(pieces, 'meeting', True)['settlements'])

    def test_survives_triviality(self):
        meeting = review_energy(4, 'meeting', True)['adopted']
        residual = review_energy(4, 'residual', True)['adopted']
        self.assertLess(meeting, 0.01)
        self.assertGreater(residual, 0.5)

    def test_perfect_verification_keeps_every_better_design_that_decides(self):
        out = review_energy(4, 'residual', True, verify=1.0)
        self.assertAlmostEqual(out['adopted'], out['in_time'], places=12)

    def test_a_worse_design_needs_a_catch_or_a_machine_that_sees(self):
        # with no catch and no stray objection, nobody disputes the flawed piece, and it passes whenever the review
        # decides; any objection to it, even a stray one, sends it to verification, which finds the flaw
        blind = review_energy(4, 'residual', False, catch=0.0, accept=1.0, verify=1.0)
        self.assertAlmostEqual(blind['adopted'], blind['in_time'], places=12)
        stray = review_energy(4, 'residual', False, catch=0.0, verify=1.0)
        self.assertLess(stray['adopted'], blind['adopted'])
        caught = review_energy(4, 'residual', False, catch=0.4)
        self.assertLess(caught['adopted'], blind['adopted'])


class MachineFirst(unittest.TestCase):

    def test_spends_nothing_and_misses_the_local_flaw(self):
        out = review_energy(4, 'machine', False)
        self.assertEqual(out['settlements'], 0.0)
        self.assertEqual(out['adopted'], 1.0)

    def test_a_machine_that_sees_the_flaw_rejects_it(self):
        self.assertEqual(review_energy(4, 'machine', False, machine_catch=1.0)['adopted'], 0.0)
        self.assertEqual(review_energy(4, 'machine', True)['adopted'], 1.0)

    def test_unknown_protocol_is_rejected(self):
        with self.assertRaises(ValueError):
            review_energy(2, 'vote', True)


class ResidualProtocol(unittest.TestCase):
    """The Residual Protocol: the machines list the pieces they cannot settle, each listed piece goes to `route`
    holders (or to Part 1's opinion holders when route is None), and people may add the flawed piece when the
    machines did not list it."""

    def test_listing_everything_with_no_route_is_residual_review(self):
        for better in (True, False):
            a = review_energy(4, 'protocol', better, lists=1.0)
            b = review_energy(4, 'residual', better)
            for key in ('adopted', 'settlements'):
                self.assertAlmostEqual(a[key], b[key], places=12)

    def test_listing_nothing_and_adding_nothing_is_the_machine(self):
        for better in (True, False):
            a = review_energy(4, 'protocol', better, lists=0.0, adds=0.0)
            b = review_energy(4, 'machine', better)
            self.assertAlmostEqual(a['adopted'], b['adopted'], places=12)
            self.assertEqual(a['settlements'], 0.0)

    def test_routing_fixes_the_holders_of_each_listed_piece(self):
        # route 2, every piece listed, a fine piece: each holder departs with chance 1 - accept = 0.1
        out = review_energy(3, 'protocol', True, lists=1.0, route=2)
        self.assertAlmostEqual(out['settlements'], 3 * 2 * 0.1, places=12)

    def test_routed_flawed_piece_worked_by_hand(self):
        # one piece, flawed, two routed holders who each catch it with 0.9, accept 0.9, verify 0.9, window wide
        says_no = 0.9 + 0.1 * 0.1
        expect = (1 - says_no) ** 2 + (1 - (1 - says_no) ** 2) * 0.1
        out = review_energy(1, 'protocol', False, lists=1.0, route=2, catch=0.9, window=1e6)
        self.assertAlmostEqual(out['adopted'], expect, places=12)

    def test_an_added_question_surfaces_the_unlisted_flaw(self):
        silent = review_energy(2, 'protocol', False, lists=0.0, adds=0.0, route=2, catch=0.9)['adopted']
        added = review_energy(2, 'protocol', False, lists=0.0, adds=1.0, route=2, catch=0.9)['adopted']
        self.assertEqual(silent, 1.0)
        self.assertLess(added, 0.2)

    def test_listing_and_adding_out_of_range_are_rejected(self):
        for kw in ({'lists': 1.5}, {'adds': -0.1}, {'route': 0}):
            with self.assertRaises(ValueError):
                review_energy(2, 'protocol', True, **kw)


if __name__ == '__main__':
    unittest.main()
