"""Checks Part 5's model: commuting webhooks give one outcome in any order, an enabling chain of
depth d reaches its fixed point from every order in d + 1 passes and not from the worst order in
d, a conflicting pair has no common fixed point, the reinvocation pass calls only webhooks that
opted in and saw a change, the closed-form share of converging orders matches enumeration, and a second
admission's patches decide the fixed point where a comparison of the returned object misses an override.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import math
import unittest

from admission import (
    admit,
    chain,
    digest,
    drop_capabilities,
    label,
    matches,
    mesh_init,
    outcomes,
    pod,
    pull_policy,
    readmission_clean,
    readmission_unchanged,
    sidecar,
    signer,
    writer,
)
from formulas import converged_share, eulerian, passes_needed


class Chains(unittest.TestCase):
    """Commuting webhooks give one outcome; depth d needs d plus one passes; passes needed matches the simulation;
    converged share matches enumeration; a conflicting pair has no common fixed point; reinvocation calls only opted
    in webhooks that saw a change."""

    def test_commuting_webhooks_give_one_outcome(self):
        for passes in (1, 2):
            self.assertEqual(len(outcomes([label, sidecar], passes=passes)), 1)

    def test_depth_d_needs_d_plus_one_passes(self):
        for d in (1, 2, 3, 4):
            ws = chain(d)
            full = admit(pod(), ws, passes=1)
            for order in itertools.permutations(ws):
                self.assertEqual(admit(pod(), order, passes=d + 1), full)
            self.assertNotEqual(admit(pod(), list(reversed(ws)), passes=d), full)

    def test_passes_needed_matches_the_simulation(self):
        ws = chain(3)
        full = admit(pod(), ws, passes=1)
        for order in itertools.permutations(range(4)):
            positions = [order.index(i) for i in range(4)]
            need = passes_needed(positions)
            self.assertEqual(admit(pod(), [ws[i] for i in order], passes=need), full)
            if need > 1:
                self.assertNotEqual(admit(pod(), [ws[i] for i in order], passes=need - 1), full)

    def test_converged_share_matches_enumeration(self):
        for n in range(1, 7):
            self.assertEqual(sum(eulerian(n, k) for k in range(n)), math.factorial(n))
            ws = chain(n - 1)
            full = admit(pod(), ws, passes=1)
            for passes in (1, 2, 3):
                hits = sum(admit(pod(), o, passes=passes) == full for o in itertools.permutations(ws))
                self.assertAlmostEqual(hits / math.factorial(n), converged_share(n, passes), places=12)
        self.assertAlmostEqual(converged_share(5, 2), (2 ** 5 - 5) / math.factorial(5), places=12)

    def test_a_conflicting_pair_has_no_common_fixed_point(self):
        for passes in (1, 2, 3, 6):
            result = outcomes([drop_capabilities, mesh_init], passes=passes)
            self.assertFalse(any(result.values()))

    def test_reinvocation_calls_only_opted_in_webhooks_that_saw_a_change(self):
        calls = []

        def counted(w):
            def f(obj):
                calls.append(w.__name__)
                return w(obj)
            return f
        # sidecar then pull_policy: pull_policy changes the object after sidecar ran, so sidecar is
        # called again (and changes nothing); nothing changes after pull_policy, so it is not.
        admit(pod(), [counted(sidecar), counted(pull_policy)], passes=2)
        self.assertEqual(calls, ['sidecar', 'pull_policy', 'sidecar'])
        calls.clear()
        admit(pod(), [counted(pull_policy), counted(sidecar)], reinvoke_if_needed=False, passes=2)
        self.assertEqual(calls, ['pull_policy', 'sidecar'])


class SecondAdmission(unittest.TestCase):
    """An override hides from a comparison of the final object; without a contested field the comparison agrees with
    the patches."""

    def test_an_override_hides_from_a_comparison_of_the_final_object(self):
        # two webhooks write one field: the admitted object is not a common fixed point, a webhook
        # still patches it on the second admission, and yet the object comes back unchanged
        ws = [writer('first', 'a'), writer('second', 'b')]
        obj = admit(pod(), ws, passes=2)
        self.assertFalse(all(w(obj) == obj for w in ws if matches(w, obj)))
        self.assertFalse(readmission_clean(obj, ws))
        self.assertTrue(readmission_unchanged(obj, ws))

    def test_without_a_contested_field_the_comparison_agrees_with_the_patches(self):
        ws = [signer, digest, sidecar]
        for order in itertools.permutations(ws):
            obj = admit(pod(), order, passes=2)
            for again in itertools.permutations(ws):
                self.assertEqual(readmission_unchanged(obj, again), readmission_clean(obj, again))


if __name__ == '__main__':
    unittest.main()
