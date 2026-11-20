"""Checks the surprisingly-popular rule (Prelec, Seung and McCoy 2017) in mixed panels. The rule picks the
answer whose actual share exceeds the share members predicted. It recovers the truth against a wrong majority
when some members hold information the rest lack; with no informed member it fails as the majority does, and
with noise but no information it is no better than a coin.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from hybrid import panel_run, surprisingly_popular


class Rule(unittest.TestCase):

    def test_two_world_case(self):
        # a third know the answer is 1 and predict that most will say 0; the rest say 0 and predict 0
        votes = [1, 1, 0, 0, 0, 0]
        predictions = [0.3, 0.3, 0.1, 0.1, 0.1, 0.1]
        self.assertEqual(surprisingly_popular(votes, predictions), 1)

    def test_no_surprise_keeps_the_majority_answer(self):
        self.assertEqual(surprisingly_popular([0, 0, 0, 1], [0.5, 0.5, 0.5, 0.5]), 0)


class Panels(unittest.TestCase):

    def test_no_informed_member_both_rules_fail(self):
        r = panel_run(0, 20, people_private=0.0, agent_rho=0.6, agent_predicts_crowd=True, trials=4000, seed=1,
                      agent_error=1.0)
        self.assertEqual(r['majority'], 0.0)
        self.assertEqual(r['surprisingly_popular'], 0.0)

    def test_noise_without_information_is_chance(self):
        r = panel_run(0, 20, people_private=0.0, agent_rho=0.3, agent_predicts_crowd=True, trials=8000, seed=2,
                      agent_error=0.7)
        self.assertLessEqual(r['surprisingly_popular'], 0.52)     # no better than a coin

    def test_informed_human_minority_turns_the_rule(self):
        r = panel_run(5, 20, people_private=0.4, agent_rho=0.6, agent_predicts_crowd=True, trials=8000, seed=3,
                      agent_error=0.7)
        self.assertLess(r['majority'], 0.3)
        self.assertGreater(r['surprisingly_popular'], r['majority'] + 0.1)


class BothStates(unittest.TestCase):

    def test_reports_false_adoption(self):
        r = panel_run(5, 20, 0.4, 0.6, True, 4000, 3, truth=0)
        self.assertIn('threshold', r)
        self.assertGreaterEqual(r['surprisingly_popular'], 0.0)

    def test_informed_people_separate_states(self):
        yes = panel_run(10, 20, 0.4, 0.3, True, 4000, 3, truth=1)
        no = panel_run(10, 20, 0.4, 0.3, True, 4000, 3, truth=0)
        self.assertGreater(yes['surprisingly_popular'], no['surprisingly_popular'] + 0.1)

    def test_no_people_cannot_separate(self):
        yes = panel_run(0, 20, 0.0, 0.6, True, 4000, 3, truth=1)
        no = panel_run(0, 20, 0.0, 0.6, True, 4000, 3, truth=0)
        self.assertAlmostEqual(yes['surprisingly_popular'], no['surprisingly_popular'], delta=0.03)


class Dilution(unittest.TestCase):

    def test_people_alone_separate_better_than_mixed_rules(self):
        yes = panel_run(5, 20, 0.4, 0.6, True, 4000, 3, truth=1)
        no = panel_run(5, 20, 0.4, 0.6, True, 4000, 3, truth=0)
        people_gap = yes['people'] - no['people']
        self.assertGreater(people_gap, yes['surprisingly_popular'] - no['surprisingly_popular'] + 0.2)

    def test_no_people_means_no_people_vote(self):
        self.assertEqual(panel_run(0, 20, 0.0, 0.6, True, 500, 3)['people'], 0.0)


class InformedAgents(unittest.TestCase):

    def test_zero_information_matches_blind_spot(self):
        a = panel_run(5, 20, 0.4, 0.6, True, 2000, 3, truth=1)
        b = panel_run(5, 20, 0.4, 0.6, True, 2000, 3, truth=1, agent_info=0.0)
        self.assertEqual(a, b)

    def test_informative_agents_help_the_midpoint_rule(self):
        def gap(info):
            y = panel_run(5, 20, 0.4, 0.3, True, 4000, 3, truth=1, agent_info=info)
            n = panel_run(5, 20, 0.4, 0.3, True, 4000, 3, truth=0, agent_info=info)
            return y['midpoint'] - n['midpoint'], y['people'] - n['people']
        low, people = gap(0.0)
        high, _ = gap(0.4)
        self.assertLess(low, people)
        self.assertGreater(high, people)


class ConditionalPredictions(unittest.TestCase):

    def test_rule_differs_from_static_threshold_with_correlated_agents(self):
        r = panel_run(5, 20, 0.4, 0.6, True, 4000, 3, truth=0)
        self.assertNotAlmostEqual(r['surprisingly_popular'], r['threshold'], places=3)

    def test_blind_spotted_agents_still_dilute_the_people(self):
        yes = panel_run(5, 20, 0.4, 0.6, True, 4000, 3, truth=1)
        no = panel_run(5, 20, 0.4, 0.6, True, 4000, 3, truth=0)
        self.assertLess(yes['surprisingly_popular'] - no['surprisingly_popular'], yes['people'] - no['people'] - 0.2)


if __name__ == '__main__':
    unittest.main()
