"""Calibration against peer review: reviewer reliability to precision, committee disagreement, shared error."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model'))

import unittest

from calibration import committee_reliability, disagreement, error_correlation, panel_agreement, precision_from_icc, shared_from_disagreement


class Precision(unittest.TestCase):

    def test_limits(self):
        self.assertAlmostEqual(precision_from_icc(0.0), 0.5)
        self.assertAlmostEqual(precision_from_icc(1.0), 1.0)

    def test_meta_analytic_reliability_gives_seventy_percent(self):
        self.assertAlmostEqual(precision_from_icc(0.34), 0.698, places=3)


class Committees(unittest.TestCase):

    def test_spearman_brown_without_shared_error(self):
        self.assertAlmostEqual(committee_reliability(0.34, 4), 4 * 0.34 / (1 + 3 * 0.34))

    def test_shared_error_lowers_reliability(self):
        self.assertLess(committee_reliability(0.34, 4, shared=0.1), committee_reliability(0.34, 4))

    def test_disagreement_falls_with_reliability(self):
        self.assertGreater(disagreement(0.4, 0.227), disagreement(0.7, 0.227))
        self.assertAlmostEqual(disagreement(1.0 - 1e-9, 0.227), 0.0, places=3)

    def test_shared_component_round_trip(self):
        rc = committee_reliability(0.34, 4, shared=0.12)
        self.assertAlmostEqual(shared_from_disagreement(0.34, 4, disagreement(rc, 0.227), 0.227), 0.12, places=3)


class ErrorsAndPanels(unittest.TestCase):

    def test_error_correlation_rises_with_shared_error(self):
        self.assertGreater(error_correlation(0.34, 0.14, 40000, 2), error_correlation(0.34, 0.0, 40000, 2) + 0.1)

    def test_sequence_raises_within_and_lowers_between_agreement(self):
        blind = panel_agreement(False, 0.34, 0.1, 15, 6000, 5)
        seq = panel_agreement(True, 0.34, 0.1, 15, 6000, 5)
        self.assertGreater(seq[0], blind[0] + 0.1)
        self.assertLess(seq[1], blind[1])


if __name__ == '__main__':
    unittest.main()
