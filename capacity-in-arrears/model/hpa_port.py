"""Plain-Python port of the Kubernetes HPA replica calculation.

Source: kubernetes/kubernetes tag v1.34.0
  pkg/controller/podautoscaler/replica_calculator.go  (GetResourceReplicas,
      getUsageRatioReplicaCount, GetExternalPerPodMetricReplicas)
  pkg/controller/podautoscaler/metrics/utilization.go (GetResourceUtilizationRatio)
  pkg/controller/podautoscaler/horizontal.go          (stabilizeRecommendation,
      convertDesiredReplicasWithRules, calculateScaleUpLimit)
Defaults (config/v1alpha1/defaults.go): sync 15 s, downscale stabilization 300 s,
tolerance 0.1, CPU initialization period 300 s, initial readiness delay 30 s.
Only the default path (spec.behavior == nil) is ported.

This file is a derivative work of the Kubernetes source files named above, translated from Go
to Python and reduced to the default path; it is not the original code.
Copyright The Kubernetes Authors. Licensed under the Apache License, Version 2.0; see the
LICENSE file at the repository root and the experiment's NOTICE.
"""
import math

TOLERANCE = 0.1
SYNC = 15
DOWNSCALE_WINDOW = 300
SCALE_UP_FACTOR = 2.0
SCALE_UP_MIN = 4.0


def within(ratio, tol=TOLERANCE):
    """Tolerances.isWithin: (1 - tol) <= ratio <= (1 + tol), with the default equal tolerances.
    (v1.30 tested |1 - ratio| <= tol, which differs in floating point at exactly 1 + tol.)"""
    return (1.0 - tol) <= ratio <= (1.0 + tol)


def utilization_ratio(usages_milli, requests_milli, target_pct):
    """GetResourceUtilizationRatio, including its integer truncation. Upstream sums integer
    millicores; the fluid model passes mean usages as floats, so the sum is math.fsum, exactly
    rounded on every Python version."""
    util = int(math.fsum(usages_milli) * 100 // sum(requests_milli))
    return util / target_pct, util


def resource_replicas(current, ready_usage, n_unready, request_milli, target_pct, tol=TOLERANCE):
    """GetResourceReplicas for pods with equal requests and no missing metrics.

    ready_usage: list of per-pod CPU usage (millicores) for pods the HPA counts as ready.
    n_unready:   pods that are Pending, or not yet ready in the HPA's sense.
    Returns (replicas, observed utilization %).
    """
    n_ready = len(ready_usage)
    ratio, util = utilization_ratio(ready_usage, [request_milli] * n_ready, target_pct)
    scale_up_with_unready = n_unready > 0 and ratio > 1.0
    if not scale_up_with_unready:
        if within(ratio, tol):
            return current, util
        return math.ceil(ratio * n_ready), util
    usages = list(ready_usage) + [0] * n_unready          # unready pods count as 0% on scale-up
    new_ratio, _ = utilization_ratio(usages, [request_milli] * len(usages), target_pct)
    if within(new_ratio, tol) or (ratio < 1.0 < new_ratio) or (ratio > 1.0 > new_ratio):
        return current, util
    new = math.ceil(new_ratio * len(usages))
    if (new_ratio < 1.0 and new > current) or (new_ratio > 1.0 and new < current):
        return current, util
    return new, util


def external_per_pod_replicas(status_replicas, usage, target_per_pod, tol=TOLERANCE):
    """GetExternalPerPodMetricReplicas (AverageValue target)."""
    ratio = usage / (target_per_pod * status_replicas)
    if within(ratio, tol):
        return status_replicas
    return math.ceil(usage / target_per_pod)


class Normalizer:
    """Default-path normalizeDesiredReplicas: downscale stabilization then scale-up limit."""

    def __init__(self, min_replicas=1, max_replicas=10 ** 6, window=DOWNSCALE_WINDOW):
        self.recs = []
        self.min, self.max, self.window = min_replicas, max_replicas, window

    def __call__(self, now, current, desired):
        best = desired
        cutoff = now - self.window
        self.recs = [(t, r) for t, r in self.recs if t >= cutoff]
        for _, r in self.recs:
            best = max(best, r)
        self.recs.append((now, desired))
        limit = int(max(SCALE_UP_FACTOR * current, SCALE_UP_MIN))
        hi = min(self.max, limit)
        return max(self.min, min(best, hi))
