"""The sensors stage: what a panel of correlated members can know.

Each member's error is driven by a latent score with one factor shared by every member: z_i = sqrt(rho) g +
sqrt(1 - rho) e_i, with g and e_i independent standard normals. A member errs when z_i falls below
Phi^-1(p), so each member errs with probability p and any two members' latent scores correlate at rho. This
is the one-factor model of the large-portfolio limit; the floor it gives is prior art (Vasicek; Li and Hai
2026 for committees of language-model judges).
"""
import math
import random
from statistics import NormalDist

from correlation import bivariate_normal_cdf

_N = NormalDist()


def latent_votes(n: int, p: float, rho: float, rng: random.Random, shared: float | None = None) -> list[bool]:
    """One panel draw. Inputs: n members, error probability p per member, latent correlation rho in [0, 1],
    a seeded rng, and optionally the shared factor g already drawn by the caller (otherwise it is drawn first).
    Output: a list of n booleans, True where the member errs. At p 1 every member errs and at p 0 none does, and
    no draw is made."""
    if p >= 1.0:
        return [True] * n
    if p <= 0.0:
        return [False] * n
    tau = _N.inv_cdf(p)
    g = rng.gauss(0.0, 1.0) if shared is None else shared
    a, b = math.sqrt(rho), math.sqrt(1.0 - rho)
    return [a * g + b * rng.gauss(0.0, 1.0) < tau for _ in range(n)]


def majority_error(n: int, p: float, rho: float, trials: int, seed: int) -> float:
    """Share of trials in which the panel's majority is wrong. A tie (exactly half wrong, for even n) counts
    as an error: the panel reaches no correct verdict. Inputs as latent_votes; trials draws from seed."""
    rng = random.Random(seed)
    wrong = 0
    for _ in range(trials):
        if 2 * sum(latent_votes(n, p, rho, rng)) >= n:
            wrong += 1
    return wrong / trials


def error_floor(p: float, rho: float) -> float:
    """The limit of majority_error as n grows: Phi(Phi^-1(p) / sqrt(rho)) for p < 0.5. At rho = 0 the floor is
    0 (independent errors average out); at rho = 1 it is p (one member's verdict, repeated)."""
    if rho <= 0.0:
        return 0.0 if p < 0.5 else (0.5 if p == 0.5 else 1.0)
    return _N.cdf(_N.inv_cdf(p) / math.sqrt(rho))


def effective_n(n: int, rho: float) -> float:
    """Independent opinions an equal-weight average of n members carries when their errors correlate at rho
    with equal variance: n / (1 + (n - 1) rho), which tends to 1 / rho."""
    return n / (1.0 + (n - 1) * rho)


def variance_floor(sigma2: float, rho: float) -> float:
    """The variance of the members' average as n grows, for members of variance sigma2 correlated at rho."""
    return sigma2 * rho


def indicator_correlation(p: float, rho: float) -> float:
    """The correlation of two members' error indicators (phi) when their latent scores correlate at rho in
    the one-factor model and each errs with probability p: (P(both err) - p^2) / (p (1 - p)). It is below rho
    for 0 < rho < 1, and it is the correlation that sets the variance of an average of votes."""
    if rho >= 1.0:
        return 1.0
    if rho == 0.0:
        return 0.0
    t = _N.inv_cdf(p)
    both = bivariate_normal_cdf(t, t, rho)
    return (both - p * p) / (p * (1.0 - p))
