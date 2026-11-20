"""An item-response null for the within-difficulty estimator.

Each model answers each question right with probability Phi(a_m - b_j): one difficulty b_j per question, normal
with variance s2, and one ability a_m per model set to match its measured accuracy. Given the question, models err
independently, so any dependence the within-difficulty estimator reports on such data is the estimator's own
artifact (difficulty left inside each stratum, sparse cells). s2 = rho / (1 - rho) matches a pooled latent
correlation rho of two models' errors.
"""
import math
import random
from statistics import NormalDist, median

from correlation import mantel_haenszel

_N = NormalDist()


def null_within_odds(accuracies: dict[str, float], n_items: int, rho: float, seed: int,
                     groups: int = 10) -> dict[str, tuple[float, float, float]]:
    """For the weakest, middle and strongest fifth of model pairs (by mean simulated accuracy), the median
    Mantel-Haenszel odds ratio within `groups` leave-pair-out difficulty strata, with all strata, without the
    hardest stratum, and without the two hardest."""
    s2 = rho / (1.0 - rho)
    scale = math.sqrt(1.0 + s2)
    rng = random.Random(seed)
    b = [rng.gauss(0.0, math.sqrt(s2)) for _ in range(n_items)]
    names = sorted(accuracies)
    x = {}
    for m in names:
        a = scale * _N.inv_cdf(min(max(accuracies[m], 0.01), 0.99))
        x[m] = [_N.cdf(a - bj) > rng.random() for bj in b]
    sim = {m: sum(v) / n_items for m, v in x.items()}
    right = [sum(x[m][j] for m in names) for j in range(n_items)]
    pairs = sorted(((sim[p] + sim[q]) / 2, p, q) for i, p in enumerate(names) for q in names[i + 1:])
    k = len(pairs) // 5
    out = {}
    for label, seg in (('weakest', pairs[:k]), ('middle', pairs[2 * k:3 * k]), ('strongest', pairs[4 * k:])):
        full, without1, without2 = [], [], []
        for _, p, q in seg:
            vp, vq = x[p], x[q]
            order = sorted(range(n_items), key=lambda j: (right[j] - vp[j] - vq[j], j))
            cells = [[0, 0, 0, 0] for _ in range(groups)]
            for rank, j in enumerate(order):
                cells[min(groups - 1, rank * groups // n_items)][(0 if vp[j] else 2) + (0 if vq[j] else 1)] += 1
            try:
                full.append(mantel_haenszel(cells)[0])
                without1.append(mantel_haenszel(cells[1:])[0])
                without2.append(mantel_haenszel(cells[2:])[0])
            except ValueError:
                continue
        out[label] = (median(full), median(without1), median(without2))
    return out
