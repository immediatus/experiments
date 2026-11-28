"""Checks Part 1's history statistic. The vertical recommender's percentile lets go of a remembered level
once the weight above the current usage falls to 1 - p of the total. With A0 the remembered weight above
the current usage and H0 the total, both in units of one sample at the start, and new samples arriving at
r per hour, each weighted 2^(t/h), the first step comes at
    s1 = h log2(1 + ln2 (A0 / (1 - p) - H0) / (r h)),
which reduces to h log2(1/(1-p)) for a long steady history. Inside the band the pair rests, and the resting
replica count is selected by what the histogram remembered: Proposition 2's continuum, picked by history.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import math
import unittest

from formulas import first_step_delay, prior_weight, step_interval
from hpa_vpa import simulate


def first_up(target, prior):
    """The hour of the first scale-up of the Part 1 pair at `target` from a histogram seeded with `prior`."""
    _, _, jumps = simulate(target, days=6, prior=prior, return_jumps=True)
    return jumps[0][0]


class FirstStep(unittest.TestCase):
    """Long steady history gives the documented interval; prior weight counts the seed and the burst; remembered
    bursts set the first step."""

    def test_long_steady_history_gives_the_documented_interval(self):
        # a stationary history of rate r has total weight r h / ln 2 in start units, all of it above after a fall
        r, h = 60.0, 24.0
        total = r * h / math.log(2)
        self.assertAlmostEqual(first_step_delay(total, total, rate=r), step_interval(h, 0.9), places=6)

    def test_prior_weight_counts_the_seed_and_the_burst(self):
        self.assertAlmostEqual(prior_weight(((2.0, 24.0, 100),)), 1.0 + 50.0)

    def test_remembered_bursts_set_the_first_step(self):
        for prior in (((2.0, 6.0, 200),), ((2.0, 6.0, 2000),), ((1.5, 24.0, 1000),)):
            w = prior_weight(prior)
            self.assertAlmostEqual(first_step_delay(w, w), first_up(0.5, prior), delta=0.2)


class RestingPoint(unittest.TestCase):
    """Inside the band history selects where the pair rests; inside the band each run rests."""

    def test_inside_the_band_history_selects_where_the_pair_rests(self):
        finals = {simulate(0.8, days=12, prior=p)[0][-1][1] for p in ((), ((2.0, 6.0, 200),), ((1.5, 24.0, 1000),))}
        self.assertEqual(len(finals), 3)

    def test_inside_the_band_each_run_rests(self):
        for p in ((), ((2.0, 6.0, 200),)):
            samples = simulate(0.8, days=20, prior=p)[0]
            self.assertEqual(samples[-1][1], samples[-6][1])


if __name__ == '__main__':
    unittest.main()
