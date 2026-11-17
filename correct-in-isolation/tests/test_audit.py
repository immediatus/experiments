"""Checks Part 6's whole-system tests: the n x n relative gain array has rows summing to one, a
three-loop matrix whose every pair looks mild can be singular, the start-time cycle of three
webhooks is found although every pair is acyclic, and the enabling depth matches the passes an
admission chain needs.

Run: python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import random
import unittest

from admission import digest, outcomes, sidecar, signer
from audit import cyclic_components, enabling_depth, pairwise_relative_gains, relative_gains
from recovery import recover


class WholeSystem(unittest.TestCase):

    def test_relative_gain_rows_sum_to_one(self):
        rng = random.Random(3)
        for n in (2, 3, 4):
            for _ in range(50):
                g = [[rng.uniform(-2, 2) for _ in range(n)] for _ in range(n)]
                r = relative_gains(g)
                if r is None:
                    continue
                for i in range(n):
                    self.assertAlmostEqual(sum(r[i]), 1.0, places=8)
                    self.assertAlmostEqual(sum(r[k][i] for k in range(n)), 1.0, places=8)

    def test_every_pair_mild_and_the_whole_singular(self):
        g = [[1, -0.5, -0.5], [-0.5, 1, -0.5], [-0.5, -0.5, 1]]
        self.assertTrue(all(abs(x - 4 / 3) < 1e-9 for x in pairwise_relative_gains(g).values()))
        self.assertIsNone(relative_gains(g))

    def test_a_three_cycle_is_invisible_to_pairs(self):
        needs = {'a': {'c'}, 'b': {'a'}, 'c': {'b'}}
        place = {'a': {0}, 'b': {1}, 'c': {2}}
        for pair in itertools.combinations('abc', 2):
            sub = {x: needs[x] & set(pair) for x in pair}
            self.assertEqual(cyclic_components(sub), [])
            self.assertEqual(recover({x: place[x] for x in pair}, sub, {0, 1, 2}), set())
        self.assertEqual(cyclic_components(needs), [{'a', 'b', 'c'}])
        self.assertEqual(recover(place, needs, {0, 1, 2}), {'a', 'b', 'c'})

    def test_enabling_depth_predicts_the_admission_chain(self):
        enables = {'sidecar': {'digest', 'signer'}, 'digest': {'signer'}}
        self.assertEqual(enabling_depth(enables), 2)
        for pair in itertools.combinations([sidecar, digest, signer], 2):
            self.assertEqual(len(outcomes(list(pair), passes=2)), 1)
        self.assertEqual(len(outcomes([sidecar, digest, signer], passes=2)), 2)
        self.assertIsNone(enabling_depth({'drop': {'mesh'}, 'mesh': {'drop'}}))


if __name__ == '__main__':
    unittest.main()
