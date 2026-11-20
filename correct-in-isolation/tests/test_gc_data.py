"""Pins the transcription of the cycle lower-bound overheads of Cai, Blackburn, Bond and Maas
(ISPASS 2022, Table "Cycle LBOs averaged over 16 benchmarks"), the source Part 1 reads beta from
for current collectors, and the elasticities taken from it.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from formulas_signal import off_heap_gain, singular_heap_share, split_relative_gain
from gc_data import CYCLE_LBO, HEAPS, pair_elasticities, peak_elasticity


class CycleLBO(unittest.TestCase):

    def test_transcription_spot_checks(self):
        self.assertEqual(HEAPS, (1.4, 1.9, 2.4, 3.0, 3.7, 4.4, 5.2, 6.0))
        self.assertEqual(CYCLE_LBO['G1'], (1.54, 1.34, 1.17, 1.14, 1.10, 1.09, 1.09, 1.09))
        self.assertEqual(CYCLE_LBO['Parallel'][:2], (1.70, 1.15))
        self.assertEqual(CYCLE_LBO['ZGC'][:3], (None, None, 1.92))

    def test_cost_never_rises_with_the_heap(self):
        for gc, row in CYCLE_LBO.items():
            vals = [v for v in row if v is not None]
            self.assertEqual(vals, sorted(vals, reverse=True), gc)

    def test_elasticities(self):
        self.assertAlmostEqual(peak_elasticity('G1')[2], 0.58, places=2)
        self.assertAlmostEqual(peak_elasticity('Parallel')[2], 1.28, places=2)
        self.assertGreater(peak_elasticity('Parallel')[2], 1)
        self.assertEqual(len(pair_elasticities('ZGC')), 5)


if __name__ == '__main__':
    unittest.main()


class OffHeapBound(unittest.TestCase):
    """With a live set that does not follow load, only memory outside the heap follows load, so theta is at
    most 1 - s_H, the share outside the heap; the gain 1 / (1 - beta theta) turns singular only when
    beta (1 - s_H) reaches one, below a heap share of 1 - 1 / beta."""

    def test_parallel_needs_a_heap_under_a_fifth_of_memory(self):
        self.assertAlmostEqual(singular_heap_share(1.28), 1 - 1 / 1.28)
        self.assertAlmostEqual(singular_heap_share(1.28), 0.21875)

    def test_beta_below_one_is_never_singular_off_heap(self):
        self.assertIsNone(singular_heap_share(0.92))
        self.assertIsNone(singular_heap_share(1.0))

    def test_off_heap_gain_follows_the_heap_share(self):
        self.assertAlmostEqual(off_heap_gain(1.28, 0.5), split_relative_gain(1.28, 0.5))
        self.assertIsNone(off_heap_gain(1.28, 0.21875))
        self.assertLess(off_heap_gain(1.28, 0.1), 0)
