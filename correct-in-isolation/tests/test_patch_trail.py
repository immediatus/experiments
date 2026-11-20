"""Checks Part 5's patch trail and conflicts. At the Request audit level the API server records each
call's patch (patch.webhook.admission.k8s.io/round_r_index_i). A field patched by two webhooks is
contested (a conflict or an override); a webhook that patches in round 1 only fields it alone writes
found input written after its first call (an enabling link in the wrong order); a match link leaves no
call at all. A webhook rewriting its own field is not an overwrite: the signer does so when its input
changes. In a conflict on one field the
admitted value is the last writer's on the last pass: with every writer IfNeeded, the last in the
order; with some IfNeeded and some Never, the last IfNeeded writer in the order, whatever the order.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import unittest

from admission import (
    admit,
    admit_patches,
    chain,
    classify_patches,
    digest,
    drop_capabilities,
    injector,
    mesh_init,
    mesh_label,
    pod,
    pull_policy,
    sidecar,
    signer,
    writer,
)


class PatchTrail(unittest.TestCase):

    def test_conflict_is_an_overwrite(self):
        for order in ([drop_capabilities, mesh_init], [mesh_init, drop_capabilities]):
            _, trail = admit_patches(pod(), order)
            contested, late = classify_patches(trail)
            self.assertEqual(contested, {('container', 'mesh-init', 'caps'): {'drop_capabilities', 'mesh_init'}})

    def test_inverted_value_link_is_late_input(self):
        ws = chain(1)
        _, trail = admit_patches(pod(), [ws[1], ws[0]])
        self.assertEqual(classify_patches(trail), ({}, {'level1'}))
        _, trail = admit_patches(pod(), [pull_policy, sidecar])
        self.assertEqual(classify_patches(trail), ({}, {'pull_policy'}))

    def test_in_order_chain_and_match_link_are_silent(self):
        ws = chain(2)
        self.assertEqual(classify_patches(admit_patches(pod(), ws)[1]), ({}, set()))
        self.assertEqual(classify_patches(admit_patches(pod(), [injector, mesh_label])[1]), ({}, set()))

    def test_stale_signature_order_shows_no_overwrite(self):
        _, trail = admit_patches(pod(), [signer, digest, sidecar])
        contested, late = classify_patches(trail)
        self.assertEqual(contested, {})
        self.assertEqual(late, {'signer', 'digest'})

    def test_patches_agree_with_admit(self):
        for order in itertools.permutations([signer, digest, sidecar]):
            self.assertEqual(admit_patches(pod(), list(order))[0], admit(pod(), list(order)))


class Conflict(unittest.TestCase):

    def winners(self, policies):
        ws = [writer('w%d' % i, 'v%d' % i, never=(p == 'Never')) for i, p in enumerate(policies)]
        out = {}
        for order in itertools.permutations(ws):
            got = dict(admit(pod(), list(order))[2])['owner']
            out[tuple(w.__name__ for w in order)] = got
        return ws, out

    def test_all_ifneeded_last_in_order_wins(self):
        ws, out = self.winners(['IfNeeded'] * 3)
        for order, got in out.items():
            self.assertEqual(got, 'v' + order[-1][1:])

    def test_all_never_last_in_order_wins(self):
        ws, out = self.winners(['Never'] * 3)
        for order, got in out.items():
            self.assertEqual(got, 'v' + order[-1][1:])

    def test_one_ifneeded_wins_every_order(self):
        ws, out = self.winners(['IfNeeded', 'Never', 'Never'])
        self.assertEqual(set(out.values()), {'v0'})

    def test_last_ifneeded_writer_wins(self):
        ws, out = self.winners(['IfNeeded', 'IfNeeded', 'Never'])
        for order, got in out.items():
            last = [n for n in order if n != 'w2'][-1]
            self.assertEqual(got, 'v' + last[1:])


if __name__ == '__main__':
    unittest.main()
