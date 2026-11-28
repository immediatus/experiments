"""A horizontal and a vertical autoscaler holding the same utilisation metric, each following its
documented rule. Units: hours for time, cores for requests and demand.

Horizontal loop (Kubernetes HPA concept page): every sync period, desired replicas =
ceil(replicas x current / target), no action while current / target is within 1 +- tol.
Vertical loop (VPA flags page): the target request is (1 + margin) times a usage percentile
(`target-cpu-percentile` 0.9) of per-pod CPU usage samples held in a histogram whose samples
lose half their weight every half_life (`cpu-histogram-decay-half-life` 24 h); no recommendation
goes below `pod-recommendation-min-cpu-millicores`, 25. Samples are taken every recommender
interval (1 min), equally weighted apart from the decay, in geometric buckets 5% wide.
Demand is steady, or follows a daily cycle of the given amplitude.
"""
import math
import random
from dataclasses import dataclass
from typing import NamedTuple, Optional


class Histogram:
    """Per-pod usage samples in geometric buckets, each weighted 2^(t / half_life) at entry, so a
    sample's weight relative to a newer one halves every half_life."""

    def __init__(self, half_life, ratio=1.05, lowest=1e-4):
        self.half_life, self.step, self.lo = half_life, math.log(ratio), math.log(lowest)
        self.weights = {}

    def add(self, value, t):
        """Add one usage sample `value`, in cores, taken at time t in hours, weighted 2^(t / half-life) so that older
        samples count half as much per half-life; values below the first bucket fall into it."""
        b = int((math.log(max(value, math.exp(self.lo))) - self.lo) / self.step)
        self.weights[b] = self.weights.get(b, 0.0) + 2.0 ** (t / self.half_life)

    def percentile(self, p):
        """The upper edge of the bucket in which the weighted p-quantile falls."""
        total = math.fsum(self.weights.values())
        acc = 0.0
        for b in sorted(self.weights):
            acc += self.weights[b]
            if acc >= p * total:
                return math.exp(self.lo + (b + 1) * self.step)
        return 0.0

    def mean(self):
        """The weighted mean usage, in cores, each bucket read at its geometric midpoint."""
        total = math.fsum(self.weights.values())
        return math.fsum(w * math.exp(self.lo + (b + 0.5) * self.step) for b, w in self.weights.items()) / total


def _demand(base, amplitude, t):
    return base * (1.0 + amplitude * math.sin(2 * math.pi * t / 24.0))

@dataclass(frozen=True)
class PairSettings:
    """Every setting of one run of the paired loops; the defaults are the series' specimen.

    Field by field:

    The horizontal loop:
        target: the horizontal loop's utilization target.
        tol: its tolerance in both directions, 0.1 by default.
        tol_up: a separate scale-up tolerance (HPAConfigurableTolerance), None for tol.
        sync_s: its sync period in seconds.

    The vertical loop:
        margin: the vertical recommendation's margin over the usage percentile.
        percentile: the usage percentile it sizes from.
        half_life: the hours in which a usage sample loses half its weight.
        sample_s: the seconds between usage samples.
        request_floor: the smallest recommendation, in cores.
        updates: None applies each recommendation to every pod at once; 'documented' follows the vertical updater.
        bound: the updater's band around the recommendation, None for the age rule alone.
        threshold: the relative difference that updates an old pod.
        min_age_h: the age in hours after which the threshold applies.

    The load:
        demand: steady demand in cores.
        amplitude: the relative amplitude of a daily demand cycle.
        noise_sigma: the shape of a lognormal factor on each pod's usage samples, 0 for none.
        noise_samples: per-pod samples the histogram receives a minute under noise.
        seed: the random seed of the noise.

    The run:
        replicas: the replicas at the start.
        days: the length of the run.
        sample_h: the hours between recorded samples.
        warmup_h: the hours excluded before the doubling time is measured.
        prior: remembered usage before the start, as (multiple of the starting usage, hours before, samples).
        supervisor_h: the period of the margin supervisor, None for none.
        change: (hour, settings): a fix to target or tol_up applied mid-run, None for none.
    """

    target: float
    tol: float = 0.1
    tol_up: Optional[float] = None
    sync_s: int = 15

    margin: float = 0.15
    percentile: float = 0.9
    half_life: float = 24.0
    sample_s: int = 60
    request_floor: float = 0.025
    updates: Optional[str] = None
    bound: Optional[float] = 0.0
    threshold: float = 0.1
    min_age_h: float = 12.0

    demand: float = 100.0
    amplitude: float = 0.0
    noise_sigma: float = 0.0
    noise_samples: int = 20
    seed: int = 1

    replicas: int = 10
    days: int = 60
    sample_h: float = 24.0
    warmup_h: float = 200.0
    prior: tuple = ()
    supervisor_h: Optional[float] = None
    change: Optional[tuple[float, dict]] = None


class PairRun(NamedTuple):
    """What one run records: samples every sample_h hours, (hour, replicas, mean request per pod in cores,
    utilization, total requested cores); the long-run doubling time in hours after the warm-up, None if the
    replicas do not reach eight times the start; every scaling action, (hour, replicas); and the margins the
    supervisor set, (hour, margin)."""
    samples: list
    doubling: Optional[float]
    jumps: list
    margins: list


def run(s: PairSettings) -> PairRun:
    """Run both loops from the horizontal loop's own steady state.

    updates None applies each new recommendation to every running pod at once. updates='documented'
    follows the vertical updater: new pods are admitted at the current recommendation, and every
    recommender interval a running pod is updated in place if its request lies outside the
    recommended bounds, modeled as recommendation x (1 +- bound), or if it is older than min_age_h
    and differs by more than threshold (VPA documentation: 12 h, 10%). bound 0 is a steady load,
    whose percentile bounds close on the target; bound None leaves only the age-and-threshold rule.
    noise_sigma > 0 multiplies each pod's usage sample by a lognormal factor of mean one and that
    shape: the vertical loop's histogram receives noise_samples such per-pod samples a minute, while
    the horizontal loop holds the mean across pods, which the factor leaves unchanged (no CPU limit
    clips the samples).
    supervisor_h, when given, runs an autonomic supervisor every that many hours: it estimates q as
    the vertical loop's histogram percentile over its mean and sets the margin to 1 / (target q) - 1,
    at least zero, the margin that rests the pair at the center of its band (Proposition 3 solved for the margin).
    prior adds remembered usage to the histogram before the start, as (multiple of the starting per-pod
    usage, hours before the start, samples): history the replica count and the utilization do not show.
    change, when given, is (hour, settings): from that hour the horizontal loop runs with the settings given,
    'target' and 'tol_up', a fix applied while the pair is in transit.
    tol_up, when given, is a separate scale-up tolerance (HPAConfigurableTolerance): the loop scales
    up only when current / target exceeds 1 + tol_up and down only when it falls below 1 - tol.
    """
    target, tol_up, margin = s.target, s.tol_up, s.margin
    rng = random.Random(s.seed)
    margins = []
    request0 = _demand(s.demand, s.amplitude, 0.0) / (s.replicas * target)
    hist = Histogram(s.half_life)
    hist.add(request0 / (1.0 + margin), -1e-9)         # history seeded at the starting usage
    for factor, hours, count in s.prior:
        for _ in range(count):
            hist.add(factor * request0 / (1.0 + margin), -hours)
    recommendation = request0
    cohorts = [[s.replicas, request0, -1e9]]                # count, request, admission hour
    steps = int(s.days * 86400 / s.sync_s)
    every = int(round(s.sample_h * 3600 / s.sync_s))
    per_sample = max(1, int(round(s.sample_s / s.sync_s)))
    start, samples, jumps = s.replicas, [], []
    for k in range(steps + 1):
        t = k * s.sync_s / 3600.0
        d = _demand(s.demand, s.amplitude, t)
        n = sum(c[0] for c in cohorts)
        requested = math.fsum(c[0] * c[1] for c in cohorts)
        if k % every == 0:
            samples.append((t, n, requested / n, d / requested, requested))
        if k == steps:
            break
        if s.change is not None and t >= s.change[0]:
            target = s.change[1].get('target', target)
            tol_up = s.change[1].get('tol_up', tol_up)
        ratio = d / requested / target
        up = s.tol if tol_up is None else tol_up
        if ratio > 1.0 + up or ratio < 1.0 - s.tol:
            desired = max(1, math.ceil(ratio * n - 1e-9))
            if desired > n:
                cohorts.append([desired - n, recommendation, t])
                if recommendation > s.request_floor:
                    jumps.append((t + s.sync_s / 3600.0, desired))
            elif desired < n:
                drop = n - desired                        # scale-down removes the newest pods first
                while drop > 0:
                    c = cohorts[-1]
                    take = min(drop, c[0])
                    c[0] -= take
                    drop -= take
                    if c[0] == 0:
                        cohorts.pop()
            n = sum(c[0] for c in cohorts)
        if s.supervisor_h and k > 0 and k % int(round(s.supervisor_h * 3600 / s.sync_s)) == 0:
            q_hat = hist.percentile(s.percentile) / hist.mean()
            margin = max(0.0, 1.0 / (target * q_hat) - 1.0)
            margins.append((t, margin))
        if k % per_sample == 0:
            if s.noise_sigma > 0:
                for _ in range(s.noise_samples):
                    hist.add(d / n * math.exp(s.noise_sigma * rng.gauss(0.0, 1.0) - s.noise_sigma ** 2 / 2.0), t)
            else:
                hist.add(d / n, t)
            recommendation = max(s.request_floor, (1.0 + margin) * hist.percentile(s.percentile))
            for c in cohorts:
                if s.updates is None:
                    c[1] = recommendation
                    continue
                off = abs(c[1] - recommendation) / recommendation
                if (s.bound is not None and off > s.bound) or ((t - c[2]) >= s.min_age_h and off > s.threshold):
                    c[1] = recommendation
            merged = {}
            for c in cohorts:                             # merge equal requests to keep the list short
                key = (round(c[1], 9), c[2] if c[2] > t - s.min_age_h else -1e9)
                if key in merged:
                    merged[key][0] += c[0]
                else:
                    merged[key] = list(c)
            cohorts = sorted(merged.values(), key=lambda c: c[2])
    return PairRun(samples, _doubling(jumps, start, s.warmup_h), jumps, margins)


def simulate(target: float, return_jumps: bool = False, **settings):
    """run() for the settings given by name, returning (samples, doubling), or (samples, doubling, jumps) with
    return_jumps: the form every section uses."""
    r = run(PairSettings(target=target, **settings))
    return (r.samples, r.doubling, r.jumps) if return_jumps else (r.samples, r.doubling)


def _doubling(jumps, start, warmup_h=200.0):
    """Long-run doubling time from the scaling actions (hour, replicas): between the first action
    after warmup_h hours, past the first steps of the staircase, and the first that reaches 64 x
    that action's replicas or the last before the request floor binds. None if replicas never
    reach 8 x the start, or do not grow inside the window."""
    if not any(n >= 8 * start for _, n in jumps):
        return None
    first = next((j for j in jumps if j[0] >= warmup_h), None)
    if first is None:
        return None
    last = next((j for j in jumps if j[0] > first[0] and j[1] >= 64 * first[1]), jumps[-1])
    if last[1] <= first[1] or last[0] <= first[0]:
        return None
    return (last[0] - first[0]) * math.log(2) / math.log(last[1] / first[1])
