"""Checks Part 5's built-in plugins: the in-tree mutating plugins run at the start of every pass, a
second pass runs whenever a webhook changed the object in the first, and the count of Proposition 37
with every built-in placed first matches the simulation. An injector feeding AlwaysPullImages:
with one pass the injected container misses the built-in's pull policy; with the second pass it gets it.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import random
import unittest

from admission import admit, fact_webhooks, pod, pull_policy, sidecar
from formulas import fact_passes


class Builtins(unittest.TestCase):
    """An injected container and the second pass; no second pass without a webhook change; count with builtins first
    matches simulation."""

    def test_an_injected_container_and_the_second_pass(self):
        one = admit(pod(), [sidecar], builtins=[pull_policy], passes=1)
        two = admit(pod(), [sidecar], builtins=[pull_policy], passes=2)
        self.assertIsNone(dict((c[0], c[2]) for c in one[0])['proxy'])
        self.assertEqual(dict((c[0], c[2]) for c in two[0])['proxy'], 'Always')

    def test_no_second_pass_without_a_webhook_change(self):
        self.assertEqual(admit(pod(), [], builtins=[pull_policy], passes=2), pull_policy(pod()))

    def test_count_with_builtins_first_matches_simulation(self):
        rng = random.Random(11)
        for _ in range(120):
            writers = ['a', 'b', 'c'][:rng.randint(2, 3)]
            facts = {}
            for f in range(rng.randint(2, 6)):
                facts['f%d' % f] = (rng.choice(writers + ['B']), {'f%d' % g for g in range(f) if rng.random() < 0.4})
            hooks = fact_webhooks(facts, writers + ['B'])
            for order in itertools.permutations(writers):
                ordered = [hooks[w] for w in order]
                full = admit(pod(), ordered, builtins=[hooks['B']], passes=len(facts) + 2)
                sim = min(p for p in range(1, len(facts) + 3)
                          if admit(pod(), ordered, builtins=[hooks['B']], passes=p) == full)
                self.assertEqual(sim, fact_passes(('B',) + order, facts), msg=str((facts, order)))


if __name__ == '__main__':
    unittest.main()
