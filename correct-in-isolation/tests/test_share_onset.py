"""Checks that the storm onset scales with the list level's share of the server: the onset is a backlog,
about 2,260 seconds of forced work, so a level with a fraction of the seats storms from that fraction of the
whole server's onset list cost (Part 6, T110).

Run: python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from relist import simulate_limited


class ShareOnset(unittest.TestCase):

    def test_half_the_server_storms_from_half_the_cost(self):
        cap = 100.0 * 122.5 / 245
        self.assertGreater(simulate_limited(57.0, capacity=cap)[0][-1], 0)
        self.assertEqual(simulate_limited(54.0, capacity=cap)[0][-1], 0)


if __name__ == '__main__':
    unittest.main()
