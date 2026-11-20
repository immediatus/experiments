"""Checks the hidden memory of Parts 1 and 3. The vertical loop sizes from a decaying histogram of past usage, which
neither the replica count nor the utilization shows. Two runs that start from the same replicas, the same
requests and the same demand, and differ only in the usage the histogram remembers, follow different
trajectories. In Part 3 the Reflector's backoff remembers recent rejections, which the queue does not
show: started raised instead of fresh, the same trigger at the same list cost runs differently.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from hpa_vpa import simulate
from relist import simulate_limited


class Memory(unittest.TestCase):

    def test_empty_prior_is_the_plain_run(self):
        self.assertEqual(simulate(0.5, days=5, prior=())[0], simulate(0.5, days=5)[0])

    def test_same_start_different_past(self):
        plain = simulate(0.5, days=20)[0]
        burst = simulate(0.5, days=20, prior=((2.0, 6.0, 200),))[0]
        self.assertEqual(plain[0][1:3], burst[0][1:3])
        self.assertNotEqual([s[1] for s in plain], [s[1] for s in burst])



class BackoffMemory(unittest.TestCase):

    def test_raised_backoff_changes_the_run_at_the_same_queue_state(self):
        fresh = simulate_limited(113.0, seed=1)
        raised = simulate_limited(113.0, seed=1, backoff_raised=True)
        self.assertNotEqual(fresh[1], raised[1])
        self.assertEqual(simulate_limited(40.0, seed=1, backoff_raised=False)[1], simulate_limited(40.0, seed=1)[1])


if __name__ == '__main__':
    unittest.main()
