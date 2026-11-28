"""Checks Part 6's incomplete descriptions. A whole-system test reads a description of the system, and a real
description misses some of it: a start-time need nobody recorded, a fact a webhook reads that its owners never
listed, an informer nobody counted, a coupling between loops nobody measured. For the assumption, the order and
the state an omission can only lower what the test computes, so a failing verdict on the incomplete description
holds for the complete one, and a passing verdict proves nothing. For the signal an omitted coupling moves the
verdict either way.

Run: python3 -m unittest discover -s tests
"""
import itertools
import os
import random
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from audit import cyclic_components
from formulas import fact_passes
from incomplete import omit_needs, omit_prereqs, random_facts, signal_flips
from percolation import gen_needs
from ratios import assumption_ratio


class Monotone(unittest.TestCase):
    """Omitted needs never make a cycle; omitted prerequisites never add passes."""

    def test_omitted_needs_never_make_a_cycle(self):
        rng = random.Random(1)
        for _ in range(200):
            needs = gen_needs(1.2, [1.0] * 60, rng)
            part = omit_needs(needs, 0.2, rng)
            self.assertTrue(all(part[i] <= needs[i] for i in needs))
            if not cyclic_components(needs):
                self.assertFalse(cyclic_components(part))
            self.assertLessEqual(assumption_ratio(part), assumption_ratio(needs) + 1e-9)

    def test_omitted_prerequisites_never_add_passes(self):
        rng = random.Random(2)
        for _ in range(300):
            writers, facts = random_facts(4, rng)
            part = omit_prereqs(facts, 0.3, rng)
            for order in itertools.permutations(writers):
                self.assertLessEqual(fact_passes(order, part), fact_passes(order, facts))


class Signal(unittest.TestCase):
    """An omitted coupling moves the verdict both ways; flip counts add up."""

    def test_an_omitted_coupling_moves_the_verdict_both_ways(self):
        out = signal_flips(3, 4000, random.Random(3))
        self.assertGreater(out['fail_to_pass'], 0)
        self.assertGreater(out['pass_to_fail'], 0)

    def test_flip_counts_add_up(self):
        out = signal_flips(4, 500, random.Random(4))
        self.assertEqual(out['fail_to_pass'] + out['fail_kept'], out['fails'])
        self.assertEqual(out['pass_to_fail'] + out['pass_kept'], 500 - out['fails'])


if __name__ == '__main__':
    unittest.main()
