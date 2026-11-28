"""Checks the TLA+ specifications in tla/ against their frozen verdicts. TLC needs Java and
tla2tools.jar, which this repository does not install, so the comparison is skipped when they are
absent; the shape of the frozen verdicts is checked always.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tla')]

import unittest

import run

EXPECTED = open(os.path.join(HERE, '..', 'tla', 'expected.txt'), encoding='utf-8').read().splitlines()


class Verdicts(unittest.TestCase):
    """Each seam holds alone and fails composed; network bound decides; tlc reproduces the frozen verdicts."""

    def test_each_seam_holds_alone_and_fails_composed(self):
        v = {line.split(' | ')[1]: line.split(' | ')[2] for line in EXPECTED}
        for alone in ('SharedSignal_horizontal', 'SharedSignal_vertical', 'NestedPair_pod_alone',
                      'NestedPair_separated', 'SharedQueue_instant', 'SharedQueue_history',
                      'StartCycle_cycle_EveryGuarantee', 'AdmissionOrder_orchestrated5'):
            self.assertEqual(v[alone], 'holds')
        for composed in ('SharedSignal_pair', 'NestedPair_nested_separated_deadline', 'SharedQueue_storm',
                         'StartCycle_cycle_AllUp', 'AdmissionOrder_contract3'):
            self.assertTrue(v[composed].startswith('violated'))

    def test_network_bound_decides(self):
        v = {line.split(' | ')[1]: line.split(' | ')[2] for line in EXPECTED}
        self.assertEqual(v['SharedQueue_net_bounded'], 'holds')
        self.assertEqual(v['SharedQueue_net_unbounded'], 'violated: NoGone')

    @unittest.skipUnless(run.tools()[0], 'TLC needs java and $TLA2TOOLS')
    def test_tlc_reproduces_the_frozen_verdicts(self):
        self.assertEqual(run.run(), EXPECTED)


if __name__ == '__main__':
    unittest.main()
