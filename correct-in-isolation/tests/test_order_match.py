"""Checks Part 5's match rules and its two cluster tests: a webhook skipped in the first round
because it does not match is never called in a later one, so a link through a match rule is not
repaired at any number of passes; the closed count of converging orders for chains with value and
match links equals enumeration; a final round with no mutation certifies the admitted object for
every webhook that was called, and only for those; a second admission of the admitted object
mutates it exactly when it is not a common fixed point of the webhooks that match it.

Run: python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import math
import unittest

from admission import (admit, admit_trace, chain, digest, drop_capabilities, final_round_clean, injector,
                       label, matches, mesh_init, mesh_label, outcomes, pod, pull_policy, readmission_clean,
                       sidecar, signer, typed_chain)
from formulas import converged_share, match_ceiling, typed_chain_share

SCENARIOS = ([label, sidecar], [sidecar, pull_policy], [sidecar, digest, signer],
             [drop_capabilities, mesh_init], [mesh_label, injector], [mesh_label, injector, pull_policy])


def fixed(obj, webhooks):
    return all(w(obj) == obj for w in webhooks if matches(w, obj))


class MatchRules(unittest.TestCase):

    def test_an_unmatched_webhook_is_never_called_in_a_later_round(self):
        _, trace = admit_trace(pod(), [injector, mesh_label], passes=3)
        self.assertNotIn('injector', [name for _, _, name, _ in trace])
        _, trace = admit_trace(pod(), [mesh_label, injector], passes=3)
        self.assertIn((0, 1, 'injector', True), trace)

    def test_a_webhook_that_stops_matching_is_skipped(self):
        def unlabel(obj):
            c, labels, a = obj
            return (c, labels - {'mesh=on'}, a)
        unlabel.__name__ = 'unlabel'
        # injector runs, then unlabel changes the object; injector no longer matches in round 1.
        _, trace = admit_trace(pod(labels=('mesh=on',)), [injector, unlabel], passes=2)
        self.assertEqual([(r, n) for r, _, n, _ in trace], [(0, 'injector'), (0, 'unlabel')])

    def test_a_match_link_is_not_repaired_at_any_number_of_passes(self):
        for passes in (1, 2, 3, 6):
            for flag in (False, True):
                result = outcomes([mesh_label, injector], reinvoke_if_needed=flag, passes=passes)
                self.assertEqual(len(result), 2)
                self.assertEqual(sum(result.values()), 1)

    def test_existing_scenarios_are_unchanged_by_match_rules(self):
        # Webhooks without a match rule match everything: the T15 counts stay as frozen.
        self.assertEqual(len(outcomes([sidecar, digest, signer], passes=2)), 2)
        self.assertEqual(len(outcomes([sidecar, pull_policy], passes=2)), 1)
        self.assertEqual(len(outcomes([sidecar, pull_policy], reinvoke_if_needed=False, passes=2)), 2)


class TypedChains(unittest.TestCase):

    def test_typed_chain_share_matches_enumeration(self):
        for n in range(2, 6):
            for kinds in itertools.product(('value', 'match'), repeat=n - 1):
                ws = typed_chain(kinds)
                full = admit(pod(), ws, passes=1)
                orders = list(itertools.permutations(ws))
                for passes in (1, 2, 3, n + 1):
                    hits = sum(admit(pod(), o, passes=passes) == full for o in orders)
                    self.assertAlmostEqual(hits / len(orders), typed_chain_share(kinds, passes), places=12,
                                           msg='%s %d' % (kinds, passes))

    def test_value_links_reduce_to_the_eulerian_share(self):
        for n in range(2, 7):
            for passes in (1, 2, 3):
                self.assertAlmostEqual(typed_chain_share(('value',) * (n - 1), passes), converged_share(n, passes),
                                       places=12)

    def test_an_all_match_chain_converges_in_one_order_in_n_factorial(self):
        for n in range(2, 7):
            for passes in (2, n + 1):
                self.assertAlmostEqual(typed_chain_share(('match',) * (n - 1), passes), 1 / math.factorial(n),
                                       places=12)

    def test_the_last_match_link_sets_the_ceiling(self):
        for n in range(2, 7):
            for kinds in itertools.product(('value', 'match'), repeat=n - 1):
                self.assertAlmostEqual(typed_chain_share(kinds, n + 1), match_ceiling(kinds), places=12)
        self.assertEqual(match_ceiling(('value', 'value', 'match')), 1 / 24)
        self.assertEqual(match_ceiling(('value',) * 4), 1.0)

    def test_typed_chain_with_value_links_only_is_the_old_chain(self):
        for d in (1, 2, 3):
            old, new = chain(d), typed_chain(('value',) * d)
            for order in itertools.permutations(range(d + 1)):
                self.assertEqual(admit(pod(), [old[i] for i in order], passes=2),
                                 admit(pod(), [new[i] for i in order], passes=2))


class ClusterTests(unittest.TestCase):

    def test_a_clean_final_round_certifies_every_called_webhook(self):
        for ws in SCENARIOS:
            for order in itertools.permutations(ws):
                obj, trace = admit_trace(pod(), order, passes=2)
                if final_round_clean(trace, passes=2):
                    called = {name for r, _, name, _ in trace if r == 0}
                    self.assertTrue(fixed(obj, [w for w in ws if w.__name__ in called]))

    def test_a_clean_final_round_misses_a_match_link(self):
        obj, trace = admit_trace(pod(), [injector, mesh_label], passes=2)
        self.assertTrue(final_round_clean(trace, passes=2))
        self.assertFalse(fixed(obj, [injector, mesh_label]))

    def test_a_dirty_final_round_can_be_a_false_alarm(self):
        obj, trace = admit_trace(pod(), [pull_policy, sidecar], passes=2)
        self.assertFalse(final_round_clean(trace, passes=2))
        self.assertTrue(fixed(obj, [pull_policy, sidecar]))

    def test_readmission_is_exact_in_every_order(self):
        for ws in SCENARIOS:
            for order in itertools.permutations(ws):
                for flag in (False, True):
                    obj = admit(pod(), order, reinvoke_if_needed=flag, passes=2)
                    for again in itertools.permutations(ws):
                        self.assertEqual(readmission_clean(obj, again), fixed(obj, ws))


if __name__ == '__main__':
    unittest.main()
