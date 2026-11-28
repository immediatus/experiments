"""Checks the fewest free slots that remove c node waits from a nested surge (Part 2). Proposition 9 prices the
slots that keep the first c rounds free of pending pods, n0 (g^c - 1). Fewer suffice: the pod loop sizes each
round from the ready pods, so once n0 + H pods are ready the rounds continue from them, and c node waits go
once n0 + H reaches N* g^(c - R). The simulation steps exactly there.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas_time import headroom_for, rounds, step_slots
from nested import penalty_bands, simulate


def simulated_steps(k, n0=64, most=1000):
    """The free-slot counts, below `most`, at which the simulated time for a k-fold surge first drops."""
    out, prev = [], simulate(k, n0=n0, headroom=0, per_node=1)
    for h in range(1, most):
        t = simulate(k, n0=n0, headroom=h, per_node=1)
        if t < prev:
            out.append(h)
        prev = min(prev, t)
    return out


class StepSlots(unittest.TestCase):
    """The penalty is a narrow band below each step; specimen steps; steps match the simulation; rounds beyond the
    surge are rejected; never more than the full cover."""

    def test_the_penalty_is_a_narrow_band_below_each_step(self):
        # a thirtyfold surge from 64 pods, one per node: only the counts just short of a step are slower than the
        # step below, by one pod's dead time, and only 53 to 55 slots are slower than no headroom at all
        bands = penalty_bands(30, 64, per_node=1)
        self.assertEqual([(lo, hi) for lo, hi, _, _ in bands], [(53, 55), (169, 175), (402, 415)])
        for lo, hi, seconds, below in bands:
            self.assertEqual(seconds - below, 90)
        self.assertEqual(simulate(30, n0=64, headroom=52, per_node=1), 1200)

    def test_specimen_steps(self):
        self.assertEqual([step_slots(c, 64, 30) for c in range(1, 5)], [56, 176, 416, 896])

    def test_steps_match_the_simulation(self):
        for k in (10, 16, 30):
            predicted = [step_slots(c, 64, k) for c in range(1, rounds(k) + 1)]
            predicted = [h for h in predicted if 0 < h < 1000]
            self.assertEqual(simulated_steps(k), sorted(set(predicted)))

    def test_rounds_beyond_the_surge_are_rejected(self):
        with self.assertRaises(ValueError):
            step_slots(4, 64, 10)

    def test_never_more_than_the_full_cover(self):
        for k in (10, 16, 30, 60):
            for c in range(1, rounds(k) + 1):
                self.assertLessEqual(step_slots(c, 64, k), headroom_for(c, 64, k))


if __name__ == '__main__':
    unittest.main()
