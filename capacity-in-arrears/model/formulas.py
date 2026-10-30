"""The closed-form results of the series, one function each, so every section that compares a
simulation with a formula uses the same formula. Numbering follows the posts.
"""
import math


def rounds(k, target=50, limit=1.0):
    """Proposition 2: provisioning rounds before a saturated CPU metric meets a k-fold overload,
    ceil(log_g(k u* r / l)) with growth factor g = l / (r u*), floored at 0.

    target is u* in percent and limit is l / r. The 1e-9 keeps a logarithm that lands a rounding
    error above a whole number from costing a round that the exact value does not.
    """
    u = target / 100.0
    g = limit / u
    return max(0, math.ceil(math.log(k * u / limit) / math.log(g) - 1e-9))


def hottest_target(k, r, limit=1.0):
    """Corollary 2: the hottest whole-percent target that can meet a k-fold overload within r
    rounds, floor(100 (l/r) k^(-1/(r+1))). A necessary condition: the tolerance band can still
    cost a round."""
    return math.floor(100 * limit * k ** (-1 / (r + 1)))


def stale_gain_bound(d):
    """Proposition 1: the exact stability bound on the gain K of x[t+1] = x[t] - K x[t-d],
    2 sin(pi / (2 (2d + 1))). The one-line ratio rule has K = 1."""
    return 2 * math.sin(math.pi / (2 * (2 * d + 1)))


def recovery_long_spike(k, rho, a, spike):
    """Proposition 7, long-spike form: seconds to recover after a k-fold spike of `spike`
    seconds at utilization rho with amplification a, spike (a k rho - 1) / (1 - a rho).
    None when a rho >= 1: the failed state is permanent (Proposition 6)."""
    if a * rho >= 1:
        return None
    return spike * (a * (k * rho) - 1) / (1 - a * rho)


def recovery_piecewise(k, rho, a, spike, tau_out):
    """Proposition 7, full form: (a k rho - 1)(spike - t0) / (1 - a rho) + tau_out / (1 - rho),
    with t0 = tau_out / (k rho - 1), the second at which waits first pass the timeout.
    None when a rho >= 1."""
    if a * rho >= 1:
        return None
    kr = k * rho
    t0 = tau_out / (kr - 1)
    return (a * kr - 1) * (spike - t0) / (1 - a * rho) + tau_out / (1 - rho)


def phi_harmonic_balance(w):
    """Harmonic-balance (describing-function) approximation to Phi(w) for w >= 1, with
    alpha = pi / (1 + w)."""
    al = math.pi / (1 + w)
    return ((1 + math.cos(al)) + (math.pi + al) * math.sin(al)) / (2 * math.pi * al)
