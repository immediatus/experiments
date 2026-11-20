"""The panel upgrade condition.

For members who err with probability p < 0.5 and correlate at rho > 0, the large-panel error floor is
Phi(Phi^-1(p) / sqrt(rho)) (sensors.error_floor). It falls exactly when |Phi^-1(p)| / sqrt(rho) rises, so an
upgrade from (p0, rho0) to (p1, rho1) improves the panel iff the relative rise in |Phi^-1(p)| exceeds half
the relative rise in rho: ln|Phi^-1(p1)| - ln|Phi^-1(p0)| > (ln rho1 - ln rho0) / 2.
"""
import math
from statistics import NormalDist

_N = NormalDist()


def _check(p: float, rho: float) -> None:
    if not 0.0 < p < 0.5:
        raise ValueError('the condition needs 0 < p < 0.5, got p = %r' % p)
    if not 0.0 < rho <= 1.0:
        raise ValueError('the condition needs 0 < rho <= 1, got rho = %r' % rho)


def upgrade_margin(p0: float, rho0: float, p1: float, rho1: float) -> float:
    """The condition in log form: (ln|Phi^-1(p1)| - ln rho1 / 2) - (ln|Phi^-1(p0)| - ln rho0 / 2). Positive
    means the panel's floor falls. Inputs: error probabilities in (0, 0.5) and correlations in (0, 1]."""
    for p, rho in ((p0, rho0), (p1, rho1)):
        _check(p, rho)
    return ((math.log(abs(_N.inv_cdf(p1))) - 0.5 * math.log(rho1))
            - (math.log(abs(_N.inv_cdf(p0))) - 0.5 * math.log(rho0)))


def upgrade_improves(p0: float, rho0: float, p1: float, rho1: float) -> bool:
    """True when upgrading every member from (p0, rho0) to (p1, rho1) lowers the large-panel error floor."""
    return upgrade_margin(p0, rho0, p1, rho1) > 0.0


def critical_elasticity(p: float) -> float:
    """The largest elasticity of correlation with respect to member error, -d ln rho / d ln p along an upgrade
    path, at which a small upgrade from error p still improves a large panel: 2 p / (|z| phi(z)), z = Phi^-1(p).
    It falls toward 2 / z^2 as p falls, so the better the members, the less correlation growth an upgrade can
    absorb."""
    if not 0.0 < p < 0.5:
        raise ValueError('p must lie in (0, 0.5), got %r' % p)
    nd = NormalDist()
    z = nd.inv_cdf(p)
    return 2.0 * p / (abs(z) * nd.pdf(z))
