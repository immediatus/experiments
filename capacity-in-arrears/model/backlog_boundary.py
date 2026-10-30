"""Deployed backlog loop (ported HPA) against the idealized boundary.

Scale: demand steps from 50 to 200 pods needed, replica ceiling 2,000, so one pod is 0.5%
and rounding does not masquerade as oscillation. A run "hunts" if pods swing by more than
30% of the needed count in the last hour of a 20-hour run; the 10% tolerance band leaves a
ripple of about +/-5% in a settled loop, which is not counted.
For each dead time and downscale window, bisection finds the smallest standing delay T/c
that does not hunt. It is compared with tau_eff * Phi(W_eff / tau_eff): Phi is the
idealized boundary of backlog_ideal.py, and the effective delays add the loop's own
sampling delay to each branch.
"""
from backlog_ideal import critical_a
from backlog_sim import run

C, NEED = 10.0, 200


def hunts(delay, dead, window, **kw):
    """Run the deployed loop at a standing delay of `delay` seconds; True if it hunts, with the run's result."""
    o = run(round(delay * C), lam0=NEED * C / 4, lam1=NEED * C, c=C, dead=dead, window=window,
            horizon=72000, step_at=600, n_max=NEED * 10, **kw)
    return (o['n_hi'] - o['n_lo']) > 0.3 * NEED, o


def boundary(dead, window, lo=2.0, hi=600.0):
    """Smallest standing delay T/c, to within 2 s, at which the deployed loop does not hunt, by bisection."""
    while hi - lo > 2.0:
        mid = (lo + hi) / 2
        if hunts(mid, dead, window)[0]:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


_PHI = {}


def phi(w):
    """Phi(w) = 1 / critical_a(w), the standing delay in dead times the idealized loop needs
    to rest at window w (0 if it rests at every delay). Cached per w to 4 decimals."""
    key = round(w, 4)
    if key not in _PHI:
        a = critical_a(w)
        _PHI[key] = 0.0 if a == float('inf') else 1.0 / a
    return _PHI[key]
