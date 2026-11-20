"""Checks the correlation estimators read from pairwise counts: the latent (tetrachoric) correlation recovers
the one-factor model's rho; it differs from the rate at which one model errs when another does; the indicator
correlation phi stays inside its Frechet-Hoeffding bounds; alignment keeps only items every model answered;
and the stored record holds counts and accuracies only.

Run: python3 -m unittest discover -s tests
"""
import json
import math
import os
import sys
import tempfile

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import random
import unittest
from statistics import NormalDist

from correlation import (
    aligned,
    bivariate_normal_cdf,
    build_record,
    load_counts,
    mantel_haenszel,
    pair_counts,
    phi_bounds,
    phi_from_counts,
    tetrachoric_from_counts,
)
from sensors import latent_votes


def _pairs(n, p, rho, seed):
    rng = random.Random(seed)
    a, b = [], []
    for _ in range(n):
        e = latent_votes(2, p, rho, rng)
        a.append(not e[0])
        b.append(not e[1])
    return a, b


class Estimators(unittest.TestCase):

    def test_tetrachoric_recovers_rho(self):
        for rho in (0.2, 0.6):
            a, b = _pairs(20000, 0.3, rho, seed=4)
            self.assertAlmostEqual(tetrachoric_from_counts(*pair_counts(a, b)), rho, delta=0.03)

    def test_conditional_error_rate_is_not_rho(self):
        a, b = _pairs(20000, 0.3, 0.2, seed=5)
        n11, n10, n01, n00 = pair_counts(a, b)
        both_err_given_one = n00 / (n00 + n01)          # P(b errs | a errs)
        self.assertGreater(abs(both_err_given_one - tetrachoric_from_counts(n11, n10, n01, n00)), 0.1)

    def test_phi_stays_within_bounds(self):
        rng = random.Random(6)
        nd = NormalDist()
        for rho in (0.3, 0.9, 0.99):
            ta, tb = nd.inv_cdf(0.1), nd.inv_cdf(0.4)          # accuracies 0.9 and 0.6
            a, b = [], []
            for _ in range(20000):
                g = rng.gauss(0, 1)
                a.append(rho ** 0.5 * g + (1 - rho) ** 0.5 * rng.gauss(0, 1) >= ta)
                b.append(rho ** 0.5 * g + (1 - rho) ** 0.5 * rng.gauss(0, 1) >= tb)
            lo, hi = phi_bounds(sum(a) / len(a), sum(b) / len(b))
            phi = phi_from_counts(*pair_counts(a, b))
            self.assertTrue(lo - 1e-9 <= phi <= hi + 1e-9)
        self.assertLess(phi_bounds(0.9, 0.6)[1], 1.0)

    def test_aligned_keeps_shared_items(self):
        out = aligned({'m1': {'q1': True, 'q2': False, 'q3': True}, 'm2': {'q2': True, 'q3': False, 'q4': True}})
        self.assertEqual(out, {'m1': [False, True], 'm2': [True, False]})


class BivariateNormal(unittest.TestCase):

    def test_orthant_closed_form(self):
        for r in (0.0, 0.3, 0.6, 0.9):
            self.assertAlmostEqual(bivariate_normal_cdf(0.0, 0.0, r), 0.25 + math.asin(r) / (2 * math.pi), places=9)


class Record(unittest.TestCase):

    def test_record_holds_counts_only(self):
        rec = build_record('src', 'unstated', {'m1': [True, False, True], 'm2': [True, True, False]})
        self.assertEqual(set(rec), {'source', 'licence', 'items', 'models', 'pairs'})
        self.assertEqual(set(rec['models']['m1']), {'accuracy', 'n'})
        pair = next(iter(rec['pairs'].values()))
        self.assertEqual(set(pair), {'n11', 'n10', 'n01', 'n00'})


class Loading(unittest.TestCase):

    def test_load_counts_round_trip(self):
        rec = build_record('src', 'unstated', {'m1': [True, False, True], 'm2': [True, True, False]})
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(rec, f)
        try:
            self.assertEqual(load_counts(f.name), rec)
        finally:
            os.unlink(f.name)


class Difficulty(unittest.TestCase):

    def _models(self):
        rng = random.Random(9)
        items = [rng.random() for _ in range(3000)]
        models = {}
        for name, skill in zip('abcdefghijklmnop', [0.01 * k for k in range(16)]):
            models[name] = [rng.random() > 0.02 + 0.9 * d * (1.0 - skill) for d in items]
        return models

    def test_record_holds_strata(self):
        rec = build_record('s', 'l', self._models(), strata=(5, 10))
        cells = rec['strata']['pairs']['a|b']
        self.assertEqual(rec['strata']['groups'], [5, 10])
        self.assertEqual(len(cells['5']), 5)
        self.assertEqual(len(cells['10']), 10)
        self.assertEqual(sum(sum(c) for c in cells['10']), 3000)


class MantelHaenszel(unittest.TestCase):

    def test_single_stratum_is_crude_odds_ratio(self):
        ratio, se = mantel_haenszel([[40, 10, 20, 30]])
        self.assertAlmostEqual(ratio, 40 * 30 / (10 * 20))
        self.assertGreater(se, 0.0)

    def test_difficulty_only_dependence_removed(self):
        rec = build_record('s', 'l', Difficulty()._models(), strata=(10,))
        c = rec['pairs']['a|b']
        crude = c['n11'] * c['n00'] / (c['n10'] * c['n01'])
        ratio, _ = mantel_haenszel(rec['strata']['pairs']['a|b']['10'])
        self.assertGreater(crude, 2.0)
        self.assertLess(abs(math.log(ratio)), 0.5 * math.log(crude))

    def test_sparse_strata_stay_finite(self):
        ratio, se = mantel_haenszel([[50, 5, 6, 0], [40, 8, 9, 1], [30, 10, 10, 3]])
        self.assertTrue(0.0 < ratio < 10.0)
        self.assertTrue(math.isfinite(se))


if __name__ == '__main__':
    unittest.main()
