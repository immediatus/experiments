"""Checks the write-back loop: an organization that learns from stated reasons as if they were the causes
converges to phi * driver + (1 - phi) * story bias (a misspecified fixed point, Esponda and Pouzo 2016), while
one that knows the stories' bias and removes it converges to the true driver; with faithful reasons both
agree, and removing a bias needs that bias to be known.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from writeback import learn, naive_limit, reason_moments


class WriteBack(unittest.TestCase):

    def test_naive_learning_converges_to_the_story_mix(self):
        got = learn(2000, phi=0.3, true_driver=1.0, story_bias=-0.8, noise=0.3, naive=True, seed=5)
        self.assertAlmostEqual(got, naive_limit(0.3, 1.0, -0.8), delta=0.05)

    def test_calibrated_learning_recovers_the_driver(self):
        got = learn(2000, phi=0.3, true_driver=1.0, story_bias=-0.8, noise=0.3, naive=False, seed=5)
        self.assertAlmostEqual(got, 1.0, delta=0.1)

    def test_faithful_reasons_need_no_correction(self):
        a = learn(2000, phi=1.0, true_driver=1.0, story_bias=-0.8, noise=0.3, naive=True, seed=5)
        self.assertAlmostEqual(a, 1.0, delta=0.05)

    def test_calibration_needs_a_known_bias(self):
        with self.assertRaises(ValueError):
            learn(10, phi=0.3, true_driver=1.0, story_bias=None, noise=0.3, naive=False, seed=5)


class Identification(unittest.TestCase):

    def test_reasons_do_not_identify_driver(self):
        mean, sd = reason_moments(0.3, 1.0, -0.8, 0.3)
        other_mean, other_sd = reason_moments(1.0, mean, 0.0, sd)
        self.assertAlmostEqual(mean, other_mean)
        self.assertAlmostEqual(sd, other_sd)


if __name__ == '__main__':
    unittest.main()
