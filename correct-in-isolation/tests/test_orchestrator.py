"""Checks Part 5's orchestrator. It submits an object for admission as a dry run, feeds the admitted object
back in, and stops once every webhook that matches it leaves it unchanged, a common fixed point; it stops
too when an admission returns an object it has seen before without one, which conflicting writers produce.
Each admission is the contract's two passes, so iterating repairs value links a single admission leaves
unfinished, and match links, which a single admission never repairs.

Run: python3 -m unittest discover -s tests
"""
import itertools
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from admission import admit, admit_trace, chain, iterate_admission, orchestrate, pod, typed_chain, writer


def common(obj, hooks):
    return all(w(obj) == obj for w in hooks if getattr(w, 'match', None) is None or w.match(obj))


class Orchestrator(unittest.TestCase):

    def test_value_chain_always_converges(self):
        hooks = chain(4)
        for order in itertools.permutations(hooks):
            out = iterate_admission(pod(), list(order))
            self.assertTrue(out['fixed_point'])
            self.assertTrue(common(out['object'], hooks))

    def test_admissions_within_the_bound(self):
        for depth in range(2, 6):
            hooks = chain(depth)
            for order in itertools.permutations(hooks):
                self.assertLessEqual(iterate_admission(pod(), list(order))['admissions'], len(hooks))

    def test_one_admission_when_already_converged(self):
        hooks = chain(3)
        out = iterate_admission(pod(), hooks)
        self.assertEqual(out['admissions'], 1)
        self.assertEqual(out['object'], admit(pod(), hooks))

    def test_reverse_order_needs_more_admissions(self):
        hooks = chain(5)
        self.assertGreater(iterate_admission(pod(), hooks[::-1])['admissions'], 1)

    def test_match_links_are_repaired(self):
        hooks = typed_chain(['match', 'match', 'match'])
        order = hooks[::-1]
        self.assertFalse(common(admit(pod(), order), hooks))
        out = iterate_admission(pod(), order)
        self.assertTrue(out['fixed_point'])
        self.assertTrue(common(out['object'], hooks))

    def test_conflicting_writers_are_detected(self):
        out = iterate_admission(pod(), [writer('a', 'A'), writer('b', 'B')])
        self.assertFalse(out['fixed_point'])
        self.assertTrue(out['cycle'])
        self.assertLessEqual(out['admissions'], 3)


if __name__ == '__main__':
    unittest.main()


class OnlineOrchestrator(unittest.TestCase):
    """The orchestrator as it must run, knowing nothing of the webhooks: it learns that an object is a fixed
    point only from a dry run that leaves it unchanged, and then creates it for real."""

    def test_confirms_with_one_more_dry_run_and_creates_once(self):
        for depth in range(2, 5):
            hooks = chain(depth)
            for order in itertools.permutations(hooks):
                oracle = iterate_admission(pod(), list(order))
                online = orchestrate(pod(), list(order))
                self.assertEqual(online['object'], oracle['object'])
                self.assertEqual(online['dry_runs'], oracle['admissions'] + 1)
                one = len(admit_trace(oracle['object'], list(order))[1])
                self.assertEqual(online['calls'], oracle['calls'] + 2 * one)

    def test_conflicting_writers_fool_the_comparison(self):
        hooks = [writer('a', 'A'), writer('b', 'B')]
        out = orchestrate(pod(), hooks)
        self.assertEqual(out['dry_runs'], 2)
        self.assertTrue(out['created'])
        self.assertFalse(out['fixed_point'])
        self.assertFalse(common(out['object'], hooks))
