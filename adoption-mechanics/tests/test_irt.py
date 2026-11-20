"""The item-response null: what the within-difficulty estimator reports when models share nothing but difficulty."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model'))

import unittest

from irt import null_within_odds


class Null(unittest.TestCase):

    def test_null_is_near_one_and_finite(self):
        acc = {'m%02d' % i: 0.5 + 0.02 * i for i in range(20)}
        out = null_within_odds(acc, 400, 0.7, 1)
        for fifth in ('weakest', 'middle', 'strongest'):
            for value in out[fifth]:
                self.assertTrue(0.8 < value < 1.8, (fifth, value))

    def test_seeded(self):
        acc = {'m%02d' % i: 0.5 + 0.02 * i for i in range(12)}
        self.assertEqual(null_within_odds(acc, 200, 0.6, 4), null_within_odds(acc, 200, 0.6, 4))


if __name__ == '__main__':
    unittest.main()
