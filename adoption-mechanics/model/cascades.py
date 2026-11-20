"""The aggregation stage's cascades, in the binary sequential model (Bikhchandani, Hirshleifer and Welch 1992).

Each member receives a binary signal (+1 or -1) that matches the true state with probability `precision`,
so one signal carries the log-likelihood ratio L = ln(precision / (1 - precision)): bounded, which is the
condition under which wrong cascades persist (Smith and Sorensen 2000). Members act in order. Every rule is
common knowledge, so an action taken outside a cascade reveals the member's signal and an action inside one
reveals nothing. The public evidence is k L, k the net count of revealed signals.

A member follows the crowd against their own signal when the evidence against it, (|k| - 1) L, exceeds
`probe_weight`: zero for a myopic member (the classic lead of two), positive for a member who values
revealing their signal to those after them, in log-odds units (the observed-player effect, March and
Ziegelmeyer 2016; people override their own signal only past about 2:1 odds, Weizsacker 2010).
"""
import math
import random
from statistics import NormalDist


def locked(lead: int, step: float, probe_weight: float) -> bool:
    """Whether a member facing the public lead `lead` (net revealed signals, positive for +1) follows it whatever
    their own signal: when the evidence against a contrary signal, (|lead| - 1) * step, exceeds probe_weight.
    step is one signal's log-likelihood ratio and probe_weight is in the same log-odds units."""
    return (abs(lead) - 1) * step > probe_weight


def _herd(signals: list[int], precision: float, probe_weight: float, probe_against: float | None,
          lead: float = 0) -> tuple[list[int], float]:
    step = math.log(precision / (1.0 - precision))
    against = probe_weight if probe_against is None else probe_against
    k = lead
    acts = []
    for s in signals:
        if locked(k, step, probe_weight if k > 0 else against):
            acts.append(1 if k > 0 else -1)
        else:
            acts.append(s)
            k += s
    return acts, k


def sequence(signals: list[int], precision: float, probe_weight: float = 0.0,
             probe_against: float | None = None, lead: float = 0) -> list[int]:
    """The actions (+1 or -1) of members who receive `signals` in order. Inputs: signals of +1 or -1, their
    precision in (0.5, 1), and the probing weight in log-odds units (0 for the classic model) that a member puts
    on their own signal before following a lead for +1; probe_against is the weight before following a lead for
    -1, equal to probe_weight unless given (unequal weights model a negativity bias). lead is a public lead the
    members already face before the first of them acts, in signal units (0 for a fresh room)."""
    return _herd(signals, precision, probe_weight, probe_against, lead)[0]


def public_lead(signals: list[int], precision: float, probe_weight: float = 0.0,
                probe_against: float | None = None) -> int:
    """The net count of signals the sequence of `sequence` reveals: it stops changing once the members lock in,
    and its sign is the verdict the sequence has settled on (0 when it has settled on none). Inputs as sequence."""
    return _herd(signals, precision, probe_weight, probe_against)[1]


def cascade_share(n: int, precision: float, probe_weight: float, trials: int, seed: int,
                  rho: float = 0.0) -> float:
    """Share of runs of n members, with the true state +1, in which the last member is locked into the wrong
    action (-1): the run has ended in a wrong cascade. Signals are drawn from `seed`. With rho > 0 the signals
    are correlated peers: each run draws one shared factor, and a member's signal is wrong when its latent
    score sqrt(rho) g + sqrt(1 - rho) e falls below Phi^-1(1 - precision). Members still treat the signals as
    independent, as in the classic model."""
    rng = random.Random(seed)
    step = math.log(precision / (1.0 - precision))
    tau = NormalDist().inv_cdf(1.0 - precision)
    a, b = math.sqrt(rho), math.sqrt(1.0 - rho)
    wrong = 0
    for _ in range(trials):
        k = 0
        g = rng.gauss(0.0, 1.0) if rho > 0.0 else 0.0
        for _ in range(n):
            if locked(k, step, probe_weight):
                break
            if rho > 0.0:
                k += -1 if a * g + b * rng.gauss(0.0, 1.0) < tau else 1
            else:
                k += 1 if rng.random() < precision else -1
        if locked(k, step, probe_weight) and k < 0:
            wrong += 1
    return wrong / trials
