"""Checks Part 5's webhook that reads outside the object: a digest pin applied to each Pod as it is
created resolves the tag at that moment, so a ReplicaSet whose pods are replaced at rate r while the
tag moves at rate lam runs two images once a replacement follows a tag move: mean 1/lam + 1/r, and
within a horizon H with probability 1 - (r e^{-lam H} - lam e^{-r H}) / (r - lam). Pinned once in the
pod template, it stays on one image until the next rollout.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import random
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas import mixed_within, time_to_mixed


def simulate(lam, r, horizon, runs=40000, seed=5):
    rng = random.Random(seed)
    hit = 0
    total = 0.0
    for _ in range(runs):
        move = rng.expovariate(lam)
        t = move + rng.expovariate(r)     # memoryless: the first replacement after the move
        total += t
        hit += t <= horizon
    return total / runs, hit / runs


class Pinning(unittest.TestCase):

    def test_mean_and_horizon_against_simulation(self):
        for lam, r in ((1.0, 1 / 3), (1 / 7, 1 / 3), (1 / 30, 1 / 3)):
            mean, share = simulate(lam, r, 30.0)
            self.assertAlmostEqual(time_to_mixed(lam, r), mean, delta=0.03 * mean)
            self.assertAlmostEqual(mixed_within(lam, r, 30.0), share, delta=0.01)

    def test_equal_rates(self):
        self.assertAlmostEqual(mixed_within(0.5, 0.5, 4.0), 1 - math.exp(-2.0) * 3.0)


if __name__ == '__main__':
    unittest.main()
