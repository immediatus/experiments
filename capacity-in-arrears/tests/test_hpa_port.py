"""Checks the port of the replica calculation against cases from the Kubernetes unit tests.

Source: kubernetes/kubernetes v1.34.0, pkg/controller/podautoscaler/replica_calculator_test.go.
Each case keeps the upstream test's name, inputs and expected result. Upstream pods have two
containers with identical requests and usage, which leaves every ratio unchanged, so one
container per pod is used here.

Not covered by the port, and so not tested: pods with unequal requests
(TestReplicaCalcTolerance); missing metrics (TestReplicaCalcMissingMetrics*); failed or
deleting pods (...IgnoresFailedPods, ...IgnoresDeletionPods); per-container metrics
(...Container...); object and pods metrics (...CMObject, ...CM); the CPU initialization window
by pod start time (...HotCpu...). Two further cases pin the documented default tolerance.

Run: python3 tests/test_hpa_port.py   or   python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), p) for p in [os.path.join('..', 'model')]]

import unittest

from hpa_port import resource_replicas, external_per_pod_replicas

REQUEST = 1000  # millicores, "1.0" upstream

CPU_CASES = [
    # name, current replicas, usage of ready pods (millicores), unready pods, target %, expected replicas, expected utilization %
    ('TestReplicaCalcScaleUp', 3, [300, 500, 700], 0, 30, 5, 50),
    ('TestReplicaCalcScaleUpUnreadyLessScale', 3, [500, 700], 1, 30, 4, 60),
    ('TestReplicaCalcScaleUpUnreadyNoScale', 3, [400], 2, 30, 3, 40),
    ('TestReplicaCalcScaleDown', 5, [100, 300, 500, 250, 250], 0, 50, 3, 28),
    ('TestReplicaCalcScaleDownExcludeUnreadyPods', 5, [100, 300, 500], 2, 50, 2, 30),
]

EXTERNAL_PER_POD_CASES = [
    # name, status replicas, metric value, target per pod, expected replicas
    ('TestReplicaCalcScaleUpPerPodCMExternal', 3, 8600, 2150, 4),
    ('TestReplicaCalcScaleDownPerPodCMExternal', 5, 8600, 2867, 3),
    ('TestReplicaCalcTolerancePerPodCMExternal', 3, 8600, 2900, 3),
]


class UpstreamCases(unittest.TestCase):

    def test_resource_cases(self):
        for name, current, usage, unready, target, want, want_util in CPU_CASES:
            with self.subTest(name):
                self.assertEqual(resource_replicas(current, usage, unready, REQUEST, target), (want, want_util))

    def test_external_per_pod_cases(self):
        for name, status, value, per_pod, want in EXTERNAL_PER_POD_CASES:
            with self.subTest(name):
                self.assertEqual(external_per_pod_replicas(status, value, per_pod), want)



class DocumentedTolerance(unittest.TestCase):
    """The default tolerance of 0.1 (kube-controller-manager --horizontal-pod-autoscaler-tolerance).

    The upstream cases above do not separate a tolerance of 0.1 from 0.2, and the dead band of
    the series depends on it exactly, so these two cases pin it from both sides."""

    def test_ratio_inside_the_band_holds(self):
        # ten saturated pods at a 92% target: 100 / 92 = 1.087, inside 1 +/- 0.1
        self.assertEqual(resource_replicas(10, [1000] * 10, 0, REQUEST, 92)[0], 10)

    def test_ratio_outside_the_band_scales(self):
        # at a 90% target: 100 / 90 = 1.111, outside the band, so 10 x 1.111 rounds up to 12
        self.assertEqual(resource_replicas(10, [1000] * 10, 0, REQUEST, 90)[0], 12)

if __name__ == '__main__':
    unittest.main()
