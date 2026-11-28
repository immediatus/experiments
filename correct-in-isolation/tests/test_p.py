"""Checks the P models in p/ against their frozen verdicts, and the abstraction they rest on. P needs the
.NET SDK and the p tool, which this repository does not install, so running the checker is skipped when
they are absent; the shape of the frozen verdicts and the soundness of the jitter abstraction are checked
always: over a grid of jitter values between one and two, the fewest rejections before a 410 are the same as
over the two extremes the P model explores.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'model')]

import importlib.util
import unittest

from formulas import fresh_rejections_to_pass

spec = importlib.util.spec_from_file_location('p_run', os.path.join(HERE, '..', 'p', 'run.py'))
p_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p_run)
EXPECTED = open(os.path.join(HERE, '..', 'p', 'expected.txt'), encoding='utf-8').read().splitlines()


def fewest_on_grid(raised, steps=40, wait_limit=15.0, retention=300.0, init=0.8, cap=30.0, reset=120.0):
    """The fewest consecutive rejections before a 410, over a grid of jitter and served waits, from a fresh or
    raised backoff: the abstraction the P model rests on, computed directly."""
    states = {(0.0, cap if raised else init, 0.0)}
    for n in range(1, 25):
        nxt = set()
        for t, d, last in states:
            t2 = t + wait_limit
            if t2 - last > reset:
                d, last = init, t2
            for i in range(steps + 1):
                t3 = round(t2 + d * (1 + i / steps), 3)
                if t3 + wait_limit > retention:
                    return n
                nxt.add((t3, min(2 * d, cap), last))
        states = nxt
    return None


class Verdicts(unittest.TestCase):
    """Bounds hold and are reached; repair race; admission; p reproduces the frozen verdicts."""

    def test_bounds_hold_and_are_reached(self):
        v = {line.split(' | ')[0]: line.split(' | ')[2] for line in EXPECTED}
        self.assertEqual(v['tcBackoffFresh'], 'holds')
        self.assertEqual(v['tcBackoffRaised'], 'holds')
        self.assertIn('410 after 11 rejections', v['tcBackoffFreshTight'])
        self.assertIn('410 after 8 rejections', v['tcBackoffRaisedTight'])

    def test_repair_race(self):
        v = {line.split(' | ')[0]: line.split(' | ')[2] for line in EXPECTED}
        self.assertTrue(v['tcRepairSelfHeal'].startswith('violated'))
        self.assertEqual(v['tcRepairPaused'], 'holds')
        self.assertEqual(v['tcRepairNudged'], 'holds')

    def test_admission(self):
        v = {line.split(' | ')[0]: line.split(' | ')[2] for line in EXPECTED}
        self.assertEqual(v['tcAdmissionNoFirstCall'], 'holds')
        self.assertTrue(v['tcAdmissionFixedPoint'].startswith('violated'))

    @unittest.skipUnless(p_run.tool(), 'P needs the p tool and the .NET SDK')
    def test_p_reproduces_the_frozen_verdicts(self):
        self.assertEqual(p_run.run(), EXPECTED)


class Abstraction(unittest.TestCase):
    """Extremes give the continuous minimum; the bounds."""

    def test_extremes_give_the_continuous_minimum(self):
        self.assertEqual(fewest_on_grid(False), fresh_rejections_to_pass(300.0)[0])
        self.assertEqual(fewest_on_grid(True), fresh_rejections_to_pass(300.0, raised=True)[0])

    def test_the_bounds(self):
        self.assertEqual(fresh_rejections_to_pass(300.0)[0], 11)
        self.assertEqual(fresh_rejections_to_pass(300.0, raised=True)[0], 8)


if __name__ == '__main__':
    unittest.main()
