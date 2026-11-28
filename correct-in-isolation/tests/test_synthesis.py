"""Checks Part 6's model: for the signal, assumption and order seams and every k from 3, a set of k
mechanisms whose every proper subset passes the seam's test while the whole fails; the passes an
order needs equal one plus the most inversions along any path of the facts the webhooks write,
checked against simulation on random dependency graphs; and the order the API server derives from
configuration names.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import random
import unittest

from admission import admit, fact_webhooks, pod, typed_chain
from audit import admission_order, config_order, cyclic_components, relative_gains
from formulas import fact_passes, informers_to_bind, pair_gain_at_singular, singular_coupling, spread_order, subset_facts, subset_gain, symmetric_gain
from recovery import recover


def converged_within(webhooks, order, passes):
    """Whether `order` admits, within `passes`, the object it reaches with passes enough."""
    full = admit(pod(), order, passes=len(webhooks) + 2)
    return admit(pod(), order, passes=passes) == full


class SeamsOfEveryOrder(unittest.TestCase):
    """Signal whole singular every proper subset regular; subset gain closed form; assumption cycle of k; order
    chain of k every proper subset converges."""

    def test_signal_whole_singular_every_proper_subset_regular(self):
        for k in range(3, 8):
            a = singular_coupling(k)
            self.assertIsNone(relative_gains(symmetric_gain(k, a)))
            for m in range(2, k):
                sub = relative_gains(symmetric_gain(m, a))
                self.assertIsNotNone(sub)
            pair = relative_gains(symmetric_gain(2, a))[0][0]
            self.assertAlmostEqual(pair, pair_gain_at_singular(k), places=12)
        self.assertAlmostEqual(pair_gain_at_singular(3), 4 / 3, places=12)
        self.assertLess(pair_gain_at_singular(6), pair_gain_at_singular(3))

    def test_subset_gain_closed_form(self):
        for k in range(3, 9):
            a = singular_coupling(k)
            for m in range(2, k):
                self.assertAlmostEqual(relative_gains(symmetric_gain(m, a))[0][0], subset_gain(m, a), places=10)
            self.assertAlmostEqual(subset_gain(k - 1, a), 2 * (k - 1) / k, places=12)
            self.assertLess(max(subset_gain(m, a) for m in range(2, k)), 2.0)

    def test_assumption_cycle_of_k(self):
        for k in range(3, 7):
            names = ['w%d' % i for i in range(k)]
            needs = {names[i]: {names[(i + 1) % k]} for i in range(k)}
            place = {n: {i} for i, n in enumerate(names)}
            self.assertEqual(len(recover(place, needs, set(range(k)))), k)
            for m in range(1, k):
                for sub in itertools.combinations(names, m):
                    sub_needs = {x: needs[x] & set(sub) for x in sub}
                    self.assertEqual(recover({x: place[x] for x in sub}, sub_needs, set(range(k))), set())
                    self.assertEqual(cyclic_components(sub_needs), [])

    def test_order_chain_of_k_every_proper_subset_converges(self):
        for k in range(3, 7):
            ws = typed_chain(('value',) * (k - 1))
            order = spread_order(k)
            whole = [ws[i] for i in order]
            self.assertFalse(converged_within(ws, whole, 2))
            self.assertTrue(converged_within(ws, whole, 3))
            for m in range(1, k):
                for sub in itertools.combinations(range(k), m):
                    induced = [ws[i] for i in order if i in sub]
                    self.assertTrue(converged_within(induced, induced, 2), msg='%d %s' % (k, sub))


class PathInversions(unittest.TestCase):
    """Passes equal one plus most path inversions; a chain is the special case."""

    def random_facts(self, rng, writers, n_facts):
        """Random facts, each written by one of `writers` and needing each earlier fact with probability 0.35."""
        facts = {}
        for f in range(n_facts):
            prereqs = {g for g in range(f) if rng.random() < 0.35}
            facts['f%d' % f] = (rng.choice(writers), {'f%d' % g for g in prereqs})
        return facts

    def test_passes_equal_one_plus_most_path_inversions(self):
        rng = random.Random(7)
        for trial in range(150):
            writers = ['a', 'b', 'c', 'd'][:rng.randint(2, 4)]
            facts = self.random_facts(rng, writers, rng.randint(2, 7))
            hooks = fact_webhooks(facts, writers)
            for order in itertools.permutations(writers):
                ordered = [hooks[w] for w in order]
                need = fact_passes(order, facts)
                self.assertTrue(converged_within(ordered, ordered, need), msg=str((facts, order)))
                if need > 1:
                    self.assertFalse(converged_within(ordered, ordered, need - 1), msg=str((facts, order)))

    def test_a_chain_is_the_special_case(self):
        facts = {'f0': ('w0', set()), 'f1': ('w1', {'f0'}), 'f2': ('w2', {'f1'})}
        self.assertEqual(fact_passes(('w2', 'w1', 'w0'), facts), 3)
        self.assertEqual(fact_passes(('w0', 'w1', 'w2'), facts), 1)
        self.assertEqual(fact_passes(('w1', 'w0', 'w2'), facts), 2)


class PairsAndCrowds(unittest.TestCase):
    """Two webhooks handing facts back and forth need three passes; informers needed for the state seam."""

    def test_two_webhooks_handing_facts_back_and_forth_need_three_passes(self):
        facts = {'f1': ('A', set()), 'f2': ('B', {'f1'}), 'f3': ('A', {'f2'}), 'f4': ('B', {'f3'})}
        hooks = fact_webhooks(facts)
        self.assertEqual(fact_passes(('B', 'A'), facts), 3)
        self.assertEqual(fact_passes(('A', 'B'), facts), 2)
        ordered = [hooks['B'], hooks['A']]
        self.assertFalse(converged_within(ordered, ordered, 2))
        self.assertTrue(converged_within(ordered, ordered, 3))

    def test_informers_needed_for_the_state_seam(self):
        # B = N_I omega / kappa must exceed the threshold: the smallest count that does.
        self.assertEqual(informers_to_bind(600.0, 100.0, 100.0), 601)
        self.assertEqual(informers_to_bind(750.0, 100.0, 100.0), 751)
        self.assertEqual(informers_to_bind(1050.0, 100.0, 100.0), 1051)
        self.assertEqual(informers_to_bind(600.0, 50.0, 100.0), 1201)


class TwoInjectors(unittest.TestCase):
    """Release name decides."""

    def test_release_name_decides(self):
        facts = {'agent container': ('vault', set()), 'agent seen by istio': ('istio', {'agent container'})}
        default = config_order({'istio-sidecar-injector': ['istio'], 'vault-agent-injector-cfg': ['vault']})
        renamed = config_order({'istio-sidecar-injector': ['istio'], 'hashicorp-vault-agent-injector-cfg': ['vault']})
        self.assertEqual(default, ['istio', 'vault'])
        self.assertEqual(fact_passes(default, facts), 2)
        self.assertEqual(fact_passes(renamed, facts), 1)


class SubsetFacts(unittest.TestCase):
    """A fact whose prerequisite has no writer is dropped; subset count matches simulation."""

    def test_a_fact_whose_prerequisite_has_no_writer_is_dropped(self):
        facts = {'f1': ('a', set()), 'f2': ('b', {'f1'}), 'f3': ('c', {'f2'}), 'f4': ('c', set())}
        self.assertEqual(set(subset_facts(facts, {'a', 'c'})), {'f1', 'f4'})
        self.assertEqual(set(subset_facts(facts, {'a', 'b', 'c'})), set(facts))

    def test_subset_count_matches_simulation(self):
        facts = {'f1': ('a', set()), 'f2': ('b', {'f1'}), 'f3': ('c', {'f2'})}
        sub = subset_facts(facts, {'b', 'c'})
        self.assertEqual(sub, {})
        self.assertEqual(fact_passes(('c', 'b'), subset_facts(facts, {'b', 'c'})), 1)


class PolicyPhase(unittest.TestCase):
    """Policies run before webhooks; direction of the link decides."""

    def test_policies_run_before_webhooks(self):
        self.assertEqual(admission_order(['zz-webhook', 'aa-webhook'], ['policy-b', 'policy-a'], ['AlwaysPullImages']),
                         ['AlwaysPullImages', 'policy-a', 'policy-b', 'aa-webhook', 'zz-webhook'])

    def test_direction_of_the_link_decides(self):
        order = admission_order(['injector'], ['policy'])
        self.assertEqual(fact_passes(order, {'f': ('policy', set()), 'g': ('injector', {'f'})}), 1)
        self.assertEqual(fact_passes(order, {'f': ('injector', set()), 'g': ('policy', {'f'})}), 2)


class ConfigurationOrder(unittest.TestCase):
    """Sorted by configuration name then listed order."""

    def test_sorted_by_configuration_name_then_listed_order(self):
        configs = {'sidecar-injector': ['inject'], 'admission-signer': ['sign', 'attest'], 'image-digest': ['pin']}
        self.assertEqual(config_order(configs), ['sign', 'attest', 'pin', 'inject'])


if __name__ == '__main__':
    unittest.main()
