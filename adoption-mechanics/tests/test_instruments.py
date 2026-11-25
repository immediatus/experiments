"""Checks the instruments of Part 3: a model's recall of a fact by its position in a long document, a review read in
overlapping parts, the fit of that recall to measured curves, a review whose groups pool their evidence blind instead
of carrying conclusions, a review that hears a two-sided debate, a single advocate or a critic before it votes, and
shared inputs from one source, whose errors move together and stop at the floor of Proposition 1.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import random
import unittest

from instruments import document_use, fact_detection, fit_recall, position_recall
from pipeline import (
    Committee,
    SharedInput,
    committee_run,
    group_review,
    pooled_review,
    shared_lead,
    stage_fates,
    verdict_margin,
)
from sensors import error_floor

GROUPS = ((5, 0.8), (5, 0.65), (5, 0.65))


class Reading(unittest.TestCase):

    def test_a_short_document_is_read_evenly(self):
        for x in (0.0, 0.3, 0.5, 1.0):
            self.assertAlmostEqual(position_recall(x, 0.0), 0.9)

    def test_the_middle_is_weakest(self):
        middle = position_recall(0.5, 0.5)
        self.assertLess(middle, position_recall(0.0, 0.5) - 0.05)
        self.assertLess(middle, position_recall(1.0, 0.5) - 0.05)

    def test_primacy_fades_near_the_window_and_recency_stays(self):
        self.assertLess(position_recall(0.0, 1.0), position_recall(0.0, 0.5) - 0.05)
        self.assertAlmostEqual(position_recall(1.0, 1.0), position_recall(1.0, 0.5), places=3)

    def test_recall_stays_a_probability(self):
        for f in (0.0, 0.25, 0.5, 0.75, 1.0, 2.0):
            for i in range(11):
                r = position_recall(i / 10, f, depth=0.9)
                self.assertGreaterEqual(r, 0.0)
                self.assertLessEqual(r, 1.0)

    def test_one_part_reads_the_whole_document(self):
        whole = fact_detection(1.0, 1, 0.0, False, 20000, 3)
        expected = sum(position_recall((i + 0.5) / 2000, 1.0) for i in range(2000)) / 2000
        self.assertAlmostEqual(whole, expected, delta=0.01)

    def test_parts_help_a_local_fact(self):
        self.assertGreater(fact_detection(1.0, 4, 0.25, False, 20000, 3), fact_detection(1.0, 1, 0.25, False, 20000, 3) + 0.05)

    def test_parts_lose_a_relational_fact(self):
        self.assertLess(fact_detection(1.0, 8, 0.25, True, 20000, 3), fact_detection(1.0, 1, 0.25, True, 20000, 3) - 0.1)

    def test_overlap_cannot_hurt_a_local_fact(self):
        self.assertGreaterEqual(fact_detection(1.0, 4, 0.5, False, 20000, 3), fact_detection(1.0, 4, 0.0, False, 20000, 3) - 0.005)


class Pooling(unittest.TestCase):

    def test_one_group_pooled_is_the_blind_review(self):
        c = Committee(cascades=False)
        a, b = random.Random(5), random.Random(5)
        for _ in range(200):
            self.assertEqual(pooled_review(c, ((15, 0.7),), a), group_review(c, ((15, 0.7),), b))

    def test_pooling_evidence_rescues_the_split_brain(self):
        c = Committee(first_speaker_silent=True)
        apart = stage_fates(c, 20000, 1, groups=GROUPS, local=0.12)
        pooled = stage_fates(c, 20000, 1, groups=GROUPS, local=0.12, pool='equal')
        self.assertLess(pooled['review'], apart['review'] - 0.1)

    def test_weights_must_be_a_known_rule(self):
        with self.assertRaises(ValueError):
            pooled_review(Committee(), GROUPS, random.Random(1), weights='loudest')


class Debate(unittest.TestCase):

    def test_debate_widens_the_gap(self):
        def gap(**kw):
            return (committee_run(Committee(first_speaker_silent=True, **kw), 20000, 1)
                    - committee_run(Committee(first_speaker_silent=True, design_better=False, **kw), 20000, 1))
        self.assertGreater(gap(debate=0.9), gap() + 0.05)

    def test_a_single_advocate_helps_the_worse_design(self):
        quiet = committee_run(Committee(first_speaker_silent=True, design_better=False), 20000, 1)
        pushed = committee_run(Committee(first_speaker_silent=True, design_better=False, advocate_lead=2.0), 20000, 1)
        self.assertGreater(pushed, quiet + 0.05)

    def test_a_strong_debate_heard_first_makes_the_panel_one_opinion(self):
        rng = random.Random(4)
        c = Committee(first_speaker_silent=True, cascades=False, debate=0.75)
        for _ in range(200):
            self.assertIn(abs(verdict_margin(c, rng)), (1.0,))

    def test_a_debate_heard_after_the_round_leaves_the_votes_alone(self):
        rng = random.Random(4)
        c = Committee(first_speaker_silent=True, cascades=False, debate=0.75, debate_after=True)
        margins = {round(abs(verdict_margin(c, rng)), 6) for _ in range(500)}
        self.assertGreater(len(margins), 3)

    def test_a_team_sharper_than_the_debate_is_not_captured(self):
        # Proposition 7 compares the debate's log-odds with each member's own: 0.75 carries 1.10, a member right 0.8 of
        # the time 1.39, so that member keeps their own vote whatever the committee's nominal precision
        c = Committee(first_speaker_silent=True, cascades=False, debate=0.75)
        for review in (group_review, pooled_review):
            rng = random.Random(4)
            margins = {round(abs(review(c, ((15, 0.8),), rng)[1]), 6) for _ in range(300)}
            self.assertGreater(len(margins), 3)

    def test_a_team_weaker_than_the_debate_is_captured(self):
        c = Committee(first_speaker_silent=True, cascades=False, debate=0.75)
        for review in (group_review, pooled_review):
            rng = random.Random(4)
            for _ in range(200):
                self.assertEqual(abs(review(c, ((15, 0.65),), rng)[1]), 1.0)

    def test_a_debate_must_be_better_than_a_coin(self):
        with self.assertRaises(ValueError):
            committee_run(Committee(debate=0.5), 10, 1)


class Calibration(unittest.TestCase):

    def test_document_use_is_the_share_of_the_oracle_gain(self):
        self.assertAlmostEqual(document_use(70.0, 50.0, 90.0), 0.5)
        self.assertEqual(document_use(40.0, 50.0, 90.0), 0.0)
        self.assertEqual(document_use(95.0, 50.0, 90.0), 1.0)

    def test_an_explicit_primacy_overrides_the_fade(self):
        self.assertGreater(position_recall(0.0, 1.0, primacy=1.0), position_recall(0.0, 1.0) + 0.2)

    def test_the_fit_recovers_a_known_curve(self):
        xs = [(i - 0.5) / 20 for i in (1, 5, 10, 15, 20)]
        ys = [position_recall(x, 1.0, base=0.7, depth=0.5, primacy=0.8, recency=0.4) for x in xs]
        base, depth, primacy, recency, rms = fit_recall(xs, ys)
        self.assertLess(rms, 0.01)
        for x in (0.0, 0.5, 1.0):
            fitted = position_recall(x, 1.0, base=base, depth=depth, primacy=primacy, recency=recency)
            self.assertAlmostEqual(fitted, position_recall(x, 1.0, base=0.7, depth=0.5, primacy=0.8, recency=0.4), delta=0.03)

    def test_recency_one_is_the_default_shape(self):
        for x in (0.0, 0.4, 1.0):
            self.assertEqual(position_recall(x, 0.7), position_recall(x, 0.7, recency=1.0))


class SharedInputs(unittest.TestCase):

    def test_a_debate_field_is_a_shared_input(self):
        a, b = random.Random(9), random.Random(9)
        c1 = Committee(first_speaker_silent=True, debate=0.75)
        c2 = Committee(first_speaker_silent=True, inputs=(SharedInput(0.75, 0.25),))
        for _ in range(300):
            self.assertEqual(verdict_margin(c1, a), verdict_margin(c2, b))

    def test_an_absent_input_changes_nothing(self):
        a, b = random.Random(9), random.Random(9)
        c1 = Committee(first_speaker_silent=True)
        c2 = Committee(first_speaker_silent=True, inputs=(SharedInput(0.95, 0.05, present=0.0),))
        for _ in range(300):
            self.assertEqual(verdict_margin(c1, a), verdict_margin(c2, b))

    def test_a_contrarian_critic_lowers_both_designs(self):
        def run(better, **kw):
            return committee_run(Committee(first_speaker_silent=True, design_better=better, **kw), 20000, 1)
        critic = (SharedInput(0.0, 0.0, weight=1.0),)
        self.assertLess(run(True, inputs=critic), run(True) - 0.05)
        self.assertLessEqual(run(False, inputs=critic), run(False))

    def test_a_shared_input_reaches_groups_and_pooled_reviews(self):
        c = Committee(first_speaker_silent=True, inputs=(SharedInput(0.95, 0.05),))
        rng = random.Random(3)
        favor, margin, info = group_review(c, GROUPS, rng, details=True)
        self.assertEqual(len({a for g in info for a in g['acts']}), 1)
        favor, margin = pooled_review(c, GROUPS, random.Random(3))
        self.assertEqual(abs(margin), 1.0)


class SharedSources(unittest.TestCase):

    def _agree(self, c, trials=4000):
        """Share of reviews in which two shared inputs say the same thing, read from the public lead they produce."""
        rng, same = random.Random(2), 0
        for _ in range(trials):
            lead, _ = shared_lead(c, 1, rng)
            same += abs(lead) > 1e-9
        return same / trials

    def test_inputs_from_one_source_agree_more_often(self):
        a = SharedInput(0.75, 0.25, source='model')
        b = SharedInput(0.75, 0.25, source='model')
        alone = self._agree(Committee(inputs=(a, b)))
        family = self._agree(Committee(inputs=(a, b), family_rho=0.8))
        self.assertGreater(family, alone + 0.1)

    def test_an_input_without_a_source_ignores_the_family(self):
        a, b = random.Random(9), random.Random(9)
        c1 = Committee(first_speaker_silent=True, inputs=(SharedInput(0.75, 0.25),))
        c2 = Committee(first_speaker_silent=True, inputs=(SharedInput(0.75, 0.25),), family_rho=0.8)
        for _ in range(300):
            self.assertEqual(verdict_margin(c1, a), verdict_margin(c2, b))

    def test_a_source_keeps_each_inputs_accuracy(self):
        c = Committee(inputs=(SharedInput(0.8, 0.2, source='model'),), family_rho=0.8)
        rng, right = random.Random(5), 0
        for _ in range(20000):
            lead, _ = shared_lead(c, 1, rng)
            right += lead > 0
        self.assertAlmostEqual(right / 20000, 0.8, delta=0.01)

    def test_roles_of_one_source_stop_at_the_floor(self):
        roles = tuple(SharedInput(0.75, 0.25, source='model') for _ in range(41))
        c = Committee(inputs=roles, family_rho=0.8)
        rng, wrong = random.Random(7), 0
        for _ in range(20000):
            lead, _ = shared_lead(c, 1, rng)
            wrong += lead < 0
        self.assertAlmostEqual(wrong / 20000, error_floor(0.25, 0.8), delta=0.02)


if __name__ == '__main__':
    unittest.main()
