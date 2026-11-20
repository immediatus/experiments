"""Checks the composed pipeline: adoption is a product of stage survivals, so raising any stage is worth
nothing while another stage is at zero; information relayed through layers falls as candor^(2 layers); groups
holding separate state reach different verdicts; and an early silence composes with cascades into a loss
neither causes alone.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import math
import random
import unittest

from pipeline import (
    Committee,
    adoption_probability,
    bikeshed,
    committee_run,
    frontier,
    group_review,
    lever_value,
    log_odds_ledger,
    partition_divergence,
    relayed_information,
    review_traces,
    stage_fates,
    verdict_margin,
    veto_crowding,
    window_survival,
)


class Ledger(unittest.TestCase):

    def test_product(self):
        self.assertAlmostEqual(adoption_probability({'a': 0.5, 'b': 0.4}), 0.2)

    def test_zero_stage_makes_every_other_lever_worthless(self):
        s = {'sensors': 0.6, 'aggregation': 0.5, 'actuator': 0.0}
        self.assertEqual(lever_value(s, 'sensors', 0.3), 0.0)

    def test_log_odds_ledger_sums_to_total(self):
        s = {'sensors': 0.6, 'aggregation': 0.5}
        self.assertAlmostEqual(sum(log_odds_ledger(s).values()), -1.2039728, places=6)   # ln 0.3


class Committees(unittest.TestCase):

    def test_hand_off_information_falls_as_a_to_the_2d(self):
        for a, d in [(0.8, 1), (0.8, 3), (0.6, 2)]:
            self.assertAlmostEqual(relayed_information(1.0, a, d), a ** (2 * d), places=9)

    def test_room_local_correlation_drives_rooms_apart(self):
        shared = partition_divergence(groups=2, members=15, rho=0.25, trials=20000, seed=2)
        local = partition_divergence(groups=2, members=15, rho=0.25, trials=20000, seed=2, local=0.12)
        self.assertGreater(local, shared + 0.02)

    def test_room_local_share_cannot_exceed_rho(self):
        with self.assertRaises(ValueError):
            partition_divergence(groups=2, members=15, rho=0.25, trials=10, seed=2, local=0.3)

    def test_verdict_margin_is_a_share_of_endorsements(self):
        rng = random.Random(4)
        margins = [verdict_margin(Committee(cascades=False, first_speaker_silent=True), rng) for _ in range(2000)]
        self.assertTrue(all(-1.0 <= m <= 1.0 for m in margins))
        self.assertAlmostEqual(math.fsum(margins) / len(margins), 2 * 0.7 - 1, delta=0.02)

    def test_one_group_is_the_one_room_review(self):
        c = Committee(first_speaker_silent=True)
        a, b = random.Random(6), random.Random(6)
        for _ in range(200):
            favor, margin = group_review(c, ((15, 0.7),), a)
            self.assertEqual(margin, verdict_margin(c, b))
            self.assertEqual(favor, margin > 0)

    def test_groups_that_decide_apart_favor_less_often(self):
        c = Committee(first_speaker_silent=True)
        rng1, rng2 = random.Random(3), random.Random(3)
        one = sum(group_review(c, ((15, 0.7),), rng1)[0] for _ in range(4000))
        apart = sum(group_review(c, ((5, 0.7), (5, 0.7), (5, 0.7)), rng2, local=0.12)[0] for _ in range(4000))
        self.assertLess(apart, one - 200)

    def test_a_better_informed_group_helps(self):
        c = Committee(first_speaker_silent=True)
        rng1, rng2 = random.Random(4), random.Random(4)
        even = sum(group_review(c, ((5, 0.7), (5, 0.7), (5, 0.7)), rng1)[0] for _ in range(4000))
        pilot = sum(group_review(c, ((5, 0.9), (5, 0.7), (5, 0.7)), rng2)[0] for _ in range(4000))
        self.assertGreater(pilot, even + 100)

    def test_stage_fates_partition_every_design(self):
        f = stage_fates(Committee(first_speaker_silent=True), 4000, 1)
        self.assertAlmostEqual(f['review'] + f['handoff'] + f['approvals'] + f['adopted'], 1.0, places=12)
        self.assertAlmostEqual(f['adopted'], committee_run(Committee(first_speaker_silent=True), 4000, 1), delta=0.03)

    def test_status_quo_in_hull_kills_at_the_approvals(self):
        f = stage_fates(Committee(first_speaker_silent=True, status_quo=(2.0, 0.2)), 2000, 1)
        self.assertEqual(f['adopted'], 0.0)
        self.assertGreater(f['approvals'], 0.5)

    def test_one_group_needs_no_reconciling(self):
        self.assertEqual(window_survival(1, 13.0, 1.0), 1.0)

    def test_more_groups_close_the_window(self):
        values = [window_survival(g, 13.0, 1.0) for g in range(1, 9)]
        self.assertTrue(all(a >= b for a, b in zip(values, values[1:])))
        self.assertLess(values[-1], 0.01)

    def test_window_matches_a_simulation_of_serial_settling(self):
        rng = random.Random(8)
        hits = sum(sum(rng.expovariate(1.0) for _ in range(10)) < 13.0 for _ in range(40000)) / 40000
        self.assertAlmostEqual(window_survival(5, 13.0, 1.0), hits, delta=0.01)

    def test_no_carry_is_the_review_without_influence(self):
        c = Committee(first_speaker_silent=True)
        groups = ((5, 0.8), (5, 0.65), (5, 0.65))
        a, b = random.Random(5), random.Random(5)
        for _ in range(300):
            self.assertEqual(group_review(c, groups, a, local=0.12), group_review(c, groups, b, local=0.12, carry=0.0))

    def test_carried_conclusions_make_groups_agree(self):
        c = Committee(first_speaker_silent=True)
        groups = ((5, 0.7), (5, 0.7), (5, 0.7))

        def split(carry):
            rng, n = random.Random(2), 0
            for _ in range(4000):
                acts = group_review(c, groups, rng, local=0.12, carry=carry, tallies=True)[2]
                n += len({t > 0 for t in acts}) > 1
            return n
        self.assertLess(split(3.0), split(0.0) - 200)

    def test_no_extra_vetoes_leave_the_case_unchanged(self):
        inside, passes = veto_crowding(0, 2000, 1)
        self.assertEqual((inside, passes), (0.0, 1.0))

    def test_more_vetoes_trap_the_status_quo(self):
        self.assertGreater(veto_crowding(6, 4000, 1)[0], veto_crowding(1, 4000, 1)[0] + 0.1)

    def test_bikeshed_whole_design_is_the_closed_form(self):
        decides, accepted, both = bikeshed(1, 20000, 3)
        exact = sum(math.comb(15, h) * 0.2 ** h * 0.8 ** (15 - h) * 0.9 ** h for h in range(16))
        self.assertAlmostEqual(accepted, exact, delta=0.01)
        self.assertLessEqual(both, min(decides, accepted) + 1e-12)

    def test_decomposing_a_design_stalls_it(self):
        values = [bikeshed(k, 4000, 3)[2] for k in (1, 2, 4, 8)]
        self.assertTrue(all(a > b for a, b in zip(values, values[1:])))
        self.assertLess(values[-1], 0.01)

    def test_the_paradox_needs_opinions_to_spread(self):
        flat = bikeshed(4, 4000, 3, steepness=0.0)[2]
        steep = bikeshed(4, 4000, 3, steepness=1.0)[2]
        self.assertGreater(flat, steep + 0.1)

    def test_traces_are_the_reviews_stage_fates_counts(self):
        for groups, local, silent in ((None, 0.0, True), (((5, 0.8), (5, 0.65), (5, 0.65)), 0.12, True), (None, 0.0, False)):
            for better in (True, False):
                c = Committee(design_better=better, first_speaker_silent=silent)
                fates = stage_fates(c, 1500, 4, groups=groups, local=local)
                traces = review_traces(c, 1500, 4, groups=groups, local=local)
                for k in ('review', 'handoff', 'approvals', 'adopted'):
                    self.assertAlmostEqual(sum(t['fate'] == k for t in traces) / 1500, fates[k], places=12)

    def test_a_trace_shows_every_vote_and_check(self):
        c = Committee(first_speaker_silent=False)
        t = review_traces(c, 1, 1)[0]
        self.assertEqual(sum(len(g['acts']) for g in t['groups']), c.members)
        self.assertEqual(t['groups'][0]['acts'][0], 1)
        self.assertEqual(len(t['relayed']), c.layers + 1)
        self.assertEqual(len(t['noise']), len(c.gate_ideals))
        self.assertAlmostEqual(t['relayed'][-1], t['relayed'][0] * c.candor ** c.layers, places=12)

    def test_a_trace_names_the_approvers_who_veto_on_priorities(self):
        t = review_traces(Committee(status_quo=(2.0, 0.2)), 1, 1)[0]
        self.assertEqual(t['vetoes'], [0, 2, 3])

    def test_partitions_diverge(self):
        one = partition_divergence(groups=1, members=15, rho=0.25, trials=20000, seed=2)
        three = partition_divergence(groups=3, members=15, rho=0.25, trials=20000, seed=2)
        self.assertEqual(one, 0.0)
        self.assertGreater(three, 0.0)

    def test_status_quo_in_hull_blocks_everything(self):
        c = Committee(status_quo=(2.0, 0.2))     # inside the hull of the default gates' ideal points
        self.assertEqual(committee_run(c, 2000, 1), 0.0)
        self.assertGreater(committee_run(Committee(), 2000, 1), 0.0)

    def _silence_cost(self, cascades, **kw):
        speak = committee_run(Committee(first_speaker_silent=False, cascades=cascades, **kw), 20000, 1)
        silent = committee_run(Committee(first_speaker_silent=True, cascades=cascades, **kw), 20000, 1)
        return speak - silent

    def test_early_silence_costs_more_with_cascades(self):
        # composition as interaction: the loss from one early silence is larger when cascades run
        self.assertGreater(self._silence_cost(True) - self._silence_cost(False), 0.05)

    def test_interaction_positive_when_evidence_is_clear_or_correlated(self):
        for kw in ({'precision': 0.8, 'rho': 0.0}, {'precision': 0.6, 'rho': 0.5}):
            self.assertGreater(self._silence_cost(True, **kw) - self._silence_cost(False, **kw), 0.0)


class WrongDesigns(unittest.TestCase):

    def test_wrong_design_adopted_less_often(self):
        good = committee_run(Committee(), 20000, 1)
        bad = committee_run(Committee(design_better=False), 20000, 1)
        self.assertLess(bad, good - 0.3)

    def test_cascades_raise_false_adoption(self):
        seq = committee_run(Committee(design_better=False, cascades=True), 20000, 1)
        blind = committee_run(Committee(design_better=False, cascades=False), 20000, 1)
        self.assertGreater(seq, blind)


class Frontier(unittest.TestCase):

    def test_undominated_points(self):
        pts = [(0.7, 0.2), (0.6, 0.1), (0.65, 0.25), (0.8, 0.3), (0.6, 0.1)]
        self.assertEqual(frontier(pts), [0, 1, 3])


class Asymmetries(unittest.TestCase):

    def test_sharper_rejection_lowers_false_adoption(self):
        base = committee_run(Committee(design_better=False), 20000, 1)
        sharp = committee_run(Committee(design_better=False, precision_worse=0.8), 20000, 1)
        self.assertLess(sharp, base)

    def test_precision_worse_ignored_for_a_better_design(self):
        self.assertEqual(committee_run(Committee(), 4000, 1), committee_run(Committee(precision_worse=0.8), 4000, 1))

    def test_resisting_a_favourable_lead_lowers_adoption(self):
        base = committee_run(Committee(first_speaker_silent=True), 20000, 1)
        biased = committee_run(Committee(first_speaker_silent=True, probe_for=1.0), 20000, 1)
        self.assertLess(biased, base)


if __name__ == '__main__':
    unittest.main()
