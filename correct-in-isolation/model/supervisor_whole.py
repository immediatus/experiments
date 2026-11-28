"""Part 6: a whole-system supervisor on the two seams that share settings, the signal and the time scale, on the
specimen of Parts 1 and 2: 16 pods at a 50% target, limit equal to request, a surge to thirty times the demand
they carry. A fix that moves where the pair rests, its target or its tolerance, keeps that demand, so the pods
change with it: 10 at a target of 0.8, 9 at the vertical loop's 0.87.
It reads both ratios of Definition 21 and chooses fixes; greedy() takes one seam at a time, joint() reads both."""
from __future__ import annotations

from typing import Optional

from formulas import covered_rounds, matched_tolerance, resting_rounds, rounds, vpa_utilisation
from nested import simulate as nested
from ratios import signal_ratio

K, N0, U0 = 30, 16, 0.5


def _pods(utilization: float) -> int:
    """The pods that carry the start's demand, N0 pods at U0, once the pair rests at `utilization`: a fix that
    moves where the pair rests changes how many pods carry the load, not the load."""
    return round(N0 * U0 / utilization)


def _state(fix: str, target: float, slots: int, metric: str = 'utilization', tol: Optional[float] = None) -> dict:
    v = vpa_utilisation()
    rest = v if tol is not None else target
    n0 = _pods(rest)
    if metric == 'load':
        r, c, s_ratio = 1, 0, 0.0
        surge = nested(K, n0=n0, metric='load', headroom=slots)
    elif tol is not None:
        k = K * v / target
        r, c = resting_rounds(K, target), covered_rounds(slots, n0, k, target)
        s_ratio = signal_ratio(target, tol_up=tol)
        surge = nested(k, n0=n0, target=target, tol=tol, headroom=slots)
    else:
        r, c = rounds(K, target), covered_rounds(slots, n0, K, target)
        s_ratio = signal_ratio(target)
        surge = nested(K, n0=n0, target=target, headroom=slots)
    return {'fix': fix, 'target': target, 'utilization': rest, 'pods': n0, 'metric': metric, 'tolerance': tol, 'slots': slots,
            'signal_ratio': s_ratio, 'time_ratio': r / (c + 1.0), 'surge_s': surge}


def _least_slots(target: float, tol: Optional[float] = None) -> int:
    """The fewest free slots that bring the time ratio to one: cover every round but the last."""
    v = vpa_utilisation()
    k = K if tol is None else K * v / target
    need = resting_rounds(K, target) if tol is not None else rounds(K, target)
    slots = 0
    while covered_rounds(slots, _pods(target if tol is None else v), k, target) < need - 1:
        slots += 1
    return slots


def greedy(band_target: float = 0.8) -> list[dict]:
    """Seams in order of their ratios, each given the smallest one-setting change that brings its own ratio to
    one, and taken again whenever a later fix pushes it back above one. The time scale's ratio, 4, is the
    larger, so headroom comes first; the signal's fix moves the target into the band; the time scale is then
    over one again and gets more headroom."""
    steps = [_state('start', 0.5, 0)]
    first = _least_slots(0.5)
    steps.append(_state('headroom', 0.5, first))
    steps.append(_state('target', band_target, first))
    steps.append(_state('headroom', band_target, _least_slots(band_target)))
    return steps


def joint(allow_load: bool = True, band_target: float = 0.8, rank: str = 'slots') -> dict:
    """Each fix of the signal seam with the fewest slots that bring the time ratio to one as well. rank 'slots'
    chooses the fewest slots, then the fastest surge; rank 'time' the fastest surge, then the fewest slots."""
    tol = matched_tolerance(0.5)
    options = [_state('target in the band', band_target, _least_slots(band_target)),
               _state('scale-up tolerance', 0.5, _least_slots(0.5, tol), tol=tol)]
    if allow_load:
        options.append(_state('load metric', 0.5, 0, metric='load'))
    ok = [o for o in options if o['signal_ratio'] <= 1.0 + 1e-9 and o['time_ratio'] <= 1.0]
    if rank == 'time':
        return min(ok, key=lambda o: (o['surge_s'], o['slots']))
    return min(ok, key=lambda o: (o['slots'], o['surge_s']))
