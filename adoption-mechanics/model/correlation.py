"""Correlation of two models' errors, read from pairwise counts only.

For two models answering the same items, n11 counts items both answer correctly, n10 items only the first
does, n01 only the second, n00 neither. Two correlations follow from these four numbers.

The latent (tetrachoric) correlation is the rho of the one-factor model: the correlation of the normal scores
whose thresholds give each model's error rate, chosen so that the bivariate normal probability of both erring
equals n00 / n. It is the rho the error floor of sensors.error_floor uses, and it can reach 1 whatever the two
error rates.

The indicator correlation phi is the Pearson correlation of the 0/1 correctness indicators. For unequal
accuracies it cannot reach 1: its range is the Frechet-Hoeffding interval of phi_bounds.

Neither is an agreement rate. The rate at which one model errs when the other does depends on the error rates
as well as on the correlation, and a pair of strong models can show a high one with a modest correlation.
"""
import json
import math
from statistics import NormalDist

_N = NormalDist()


def pair_counts(a: list[bool], b: list[bool]) -> tuple[int, int, int, int]:
    """(n11, n10, n01, n00) over two equal-length lists of correctness indicators (True = correct)."""
    if len(a) != len(b):
        raise ValueError('the two models must be scored on the same items')
    n11 = sum(1 for x, y in zip(a, b) if x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if y and not x)
    return n11, n10, n01, len(a) - n11 - n10 - n01


def bivariate_normal_cdf(h: float, k: float, r: float, steps: int = 400) -> float:
    """P(Z1 < h, Z2 < k) for standard normals Z1, Z2 with correlation r in (-1, 1): Phi(h) Phi(k) plus the
    integral over s from 0 to r of the bivariate density at (h, k) (Plackett's identity), by Simpson's rule with
    `steps` intervals."""
    def dens(s):
        q = 1.0 - s * s
        return math.exp(-(h * h - 2.0 * s * h * k + k * k) / (2.0 * q)) / (2.0 * math.pi * math.sqrt(q))
    if steps % 2:
        steps += 1
    dx = r / steps
    total = math.fsum([dens(0.0), dens(r)] + [(4.0 if i % 2 else 2.0) * dens(i * dx) for i in range(1, steps)])
    return _N.cdf(h) * _N.cdf(k) + total * dx / 3.0


def tetrachoric_from_counts(n11: int, n10: int, n01: int, n00: int, cap: float = 0.999) -> float:
    """The latent correlation of two models' errors from their pair counts, by bisection on rho in
    [-cap, cap]. Needs every margin nonzero."""
    n = n11 + n10 + n01 + n00
    err_a, err_b, both = (n01 + n00) / n, (n10 + n00) / n, n00 / n
    if not (0.0 < err_a < 1.0 and 0.0 < err_b < 1.0):
        raise ValueError('each model must err on some items and answer some correctly')
    h, k = _N.inv_cdf(err_a), _N.inv_cdf(err_b)
    lo, hi = -cap, cap
    if both <= bivariate_normal_cdf(h, k, lo):
        return lo
    if both >= bivariate_normal_cdf(h, k, hi):
        return hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if bivariate_normal_cdf(h, k, mid) < both:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def phi_from_counts(n11: int, n10: int, n01: int, n00: int) -> float:
    """The indicator correlation phi of two models' correctness from their pair counts (n11 both right, n10 only
    the first, n01 only the second, n00 neither): the Pearson correlation of the 0/1 indicators, in [-1, 1], or 0
    when a margin is empty."""
    den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    return (n11 * n00 - n10 * n01) / den if den else 0.0


def phi_bounds(p_i: float, p_j: float) -> tuple[float, float]:
    """The Frechet-Hoeffding range of phi for indicators with success probabilities p_i and p_j."""
    lo_p, hi_p = min(p_i, p_j), max(p_i, p_j)
    upper = math.sqrt(lo_p * (1.0 - hi_p) / (hi_p * (1.0 - lo_p)))
    lower = -min(math.sqrt(p_i * p_j / ((1.0 - p_i) * (1.0 - p_j))),
                 math.sqrt((1.0 - p_i) * (1.0 - p_j) / (p_i * p_j)))
    return lower, upper


def aligned(errors: dict[str, dict[str, bool]]) -> dict[str, list[bool]]:
    """Each model's correctness indicators over the items every model answered, in sorted item order."""
    shared = set.intersection(*(set(v) for v in errors.values())) if errors else set()
    items = sorted(shared)
    return {m: [errors[m][i] for i in items] for m in errors}


def build_record(source: str, licence: str, errors_by_model: dict[str, list[bool]], strata: tuple = ()) -> dict:
    """The stored summary: per model its accuracy and item count, per pair its four counts. No item text, no
    answers, no per-item vectors. With strata, a tuple of group counts such as (5, 10), it also stores per pair
    the four counts within each group of items of similar difficulty, for each group count, so that dependence
    can be measured with difficulty held nearly fixed. Difficulty is the share of the other models, all but the
    pair, that answered the item right, so the pair's own answers do not define its strata; the groups are of
    equal size."""
    names = sorted(errors_by_model)
    n = len(errors_by_model[names[0]]) if names else 0
    models = {m: {'accuracy': sum(v) / len(v), 'n': len(v)} for m, v in errors_by_model.items()}
    pairs = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            n11, n10, n01, n00 = pair_counts(errors_by_model[a], errors_by_model[b])
            pairs['%s|%s' % (a, b)] = {'n11': n11, 'n10': n10, 'n01': n01, 'n00': n00}
    record = {'source': source, 'licence': licence, 'items': n, 'models': models, 'pairs': pairs}
    groups = [g for g in strata if g > 0]
    if groups and len(names) >= 3:
        right = [sum(errors_by_model[m][j] for m in names) for j in range(n)]
        by_pair = {}
        for i, a in enumerate(names):
            va = errors_by_model[a]
            for b in names[i + 1:]:
                vb = errors_by_model[b]
                ease = [(right[j] - va[j] - vb[j]) / (len(names) - 2) for j in range(n)]
                order = sorted(range(n), key=lambda j: (ease[j], j))
                entry = {}
                for g in groups:
                    cells = [[0, 0, 0, 0] for _ in range(g)]
                    for rank, j in enumerate(order):
                        cells[min(g - 1, rank * g // n)][(0 if va[j] else 2) + (0 if vb[j] else 1)] += 1
                    entry[str(g)] = cells
                by_pair['%s|%s' % (a, b)] = entry
        record['strata'] = {'groups': groups, 'by': 'share of the other models right', 'pairs': by_pair}
    return record


def mantel_haenszel(cells: list[list[int]]) -> tuple[float, float]:
    """The Mantel-Haenszel common odds ratio of two models' errors across strata, and the standard error of its
    logarithm (Robins, Breslow and Greenland). Unlike a tetrachoric correlation per stratum, it stays finite
    when a stratum has no item both models got wrong. cells: per stratum [n11, n10, n01, n00]."""
    sr = ss = spr = spsqr = sqs = 0.0
    for n11, n10, n01, n00 in cells:
        n = n11 + n10 + n01 + n00
        if n == 0:
            continue
        r, s_, p_, q = n11 * n00 / n, n10 * n01 / n, (n11 + n00) / n, (n10 + n01) / n
        sr += r
        ss += s_
        spr += p_ * r
        spsqr += p_ * s_ + q * r
        sqs += q * s_
    if sr == 0.0 or ss == 0.0:
        raise ValueError('the odds ratio is not finite: no concordant or no discordant weight')
    var = spr / (2 * sr * sr) + spsqr / (2 * sr * ss) + sqs / (2 * ss * ss)
    return sr / ss, math.sqrt(var)


def load_counts(path: str) -> dict:
    """The stored record written by build_record (data/model_errors.json), read as UTF-8."""
    with open(path, encoding='utf-8') as f:
        return json.load(f)
