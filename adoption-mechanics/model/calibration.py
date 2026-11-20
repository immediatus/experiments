"""Calibration of the member model against scientific peer review, the closest public analogue of a design review.

A reviewer's score is s = theta + u + e: theta the proposal's true quality (variance r, the inter-reviewer
reliability measured across independent reviewers), u an error shared by the reviewers of one committee (variance
`shared`, from discussion, anchoring or a shared frame), e private noise (the rest of a unit variance). A binary
judgment is the sign of the score, and it is right when it matches the sign of theta.
"""
import math
import random
from statistics import NormalDist

from cascades import sequence
from correlation import tetrachoric_from_counts

_N = NormalDist()


def precision_from_icc(r: float) -> float:
    """Probability that one reviewer's yes-or-no judgment matches the truth when the score's reliability is r and
    half the proposals are better than the bar: 1/2 + arcsin(sqrt(r)) / pi (the bivariate normal orthant)."""
    return 0.5 + math.asin(math.sqrt(r)) / math.pi


def committee_reliability(r: float, k: int, shared: float = 0.0) -> float:
    """Correlation between the mean scores of two independent committees of k reviewers: r / (r + shared +
    (1 - r - shared) / k). Without shared error this is the Spearman-Brown formula."""
    return r / (r + shared + (1.0 - r - shared) / k)


def _both_above(t: float, rho: float, steps: int = 4000) -> float:
    """P(X > t, Y > t) for standard normals with correlation rho in [0, 1], as the integral over x > t of
    phi(x) P(Y > t | x), by Simpson's rule on [t, t + 10]; exact at rho = 1."""
    if rho >= 1.0:
        return 1.0 - _N.cdf(t)
    s = math.sqrt(1.0 - rho * rho)
    h = 10.0 / steps

    def f(x):
        return _N.pdf(x) * (1.0 - _N.cdf((t - rho * x) / s))
    total = f(t) + f(t + 10.0)
    for i in range(1, steps):
        total += (4.0 if i % 2 else 2.0) * f(t + i * h)
    return total * h / 3.0


def disagreement(committee_r: float, acceptance: float) -> float:
    """Share of proposals on which two committees whose mean scores correlate at committee_r disagree, when each
    accepts its top `acceptance` share."""
    t = _N.inv_cdf(1.0 - acceptance)
    return 2.0 * (acceptance - _both_above(t, committee_r))


def shared_from_disagreement(r: float, k: int, observed: float, acceptance: float) -> float:
    """The within-committee shared variance that makes committees of k reviewers with reliability r disagree on the
    observed share of proposals."""
    lo, hi = 0.0, 0.999
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if disagreement(mid, acceptance) > observed:
            lo = mid
        else:
            hi = mid
    rc = (lo + hi) / 2.0
    return (r / rc - r - (1.0 - r) / k) / (1.0 - 1.0 / k)


def error_correlation(r: float, shared: float, trials: int, seed: int) -> float:
    """Latent (tetrachoric) correlation of two reviewers' errors in one committee, by simulation."""
    rng = random.Random(seed)
    n = [0, 0, 0, 0]
    s_t, s_u, s_e = math.sqrt(r), math.sqrt(shared), math.sqrt(1.0 - r - shared)
    for _ in range(trials):
        theta = rng.gauss(0.0, s_t)
        u = rng.gauss(0.0, s_u)
        ea = (theta + u + rng.gauss(0.0, s_e) > 0) != (theta > 0)
        eb = (theta + u + rng.gauss(0.0, s_e) > 0) != (theta > 0)
        n[(2 if ea else 0) + (1 if eb else 0)] += 1
    return tetrachoric_from_counts(n[0], n[1], n[2], n[3])


def panel_agreement(sequential: bool, r: float, shared: float, members: int, trials: int, seed: int,
                    precision: float = 0.7) -> tuple[float, float]:
    """Two panels judge the same proposal, each with its own shared error: (mean share of a panel's votes that agree
    with its own majority, share of trials in which the two panels reach the same verdict). Sequential panels vote
    in order with the cascade rule for signals of the given precision; blind panels vote at once."""
    rng = random.Random(seed)
    s_t, s_u, s_e = math.sqrt(r), math.sqrt(shared), math.sqrt(1.0 - r - shared)
    within = between = 0.0
    for _ in range(trials):
        theta = rng.gauss(0.0, s_t)
        verdicts = []
        for _panel in range(2):
            u = rng.gauss(0.0, s_u)
            signals = [1 if theta + u + rng.gauss(0.0, s_e) > 0 else -1 for _ in range(members)]
            acts = sequence(signals, precision) if sequential else signals
            verdict = 1 if sum(acts) > 0 else -1
            within += sum(1 for a in acts if a == verdict) / members
            verdicts.append(verdict)
        between += verdicts[0] == verdicts[1]
    return within / (2 * trials), between / trials
