"""Checks the seam audit command, which reads a cluster's objects as `kubectl get ... -o json` prints them, and a
description of what objects do not record, and runs the five whole-system tests of Part 6.

Run: python3 -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'audit'), os.path.join(HERE, '..', 'model')]

import tempfile
import unittest

import seam_audit as sa


def webhook_config(kind, name, hooks):
    return {'kind': kind, 'metadata': {'name': name}, 'webhooks': hooks}


def hook(name, ns, fail='Fail', ns_selector=None, obj_selector=None, reinvoke=None, pods=True):
    h = {'name': name, 'clientConfig': {'service': {'namespace': ns, 'name': name}},
         'rules': [{'apiGroups': [''], 'apiVersions': ['v1'], 'operations': ['CREATE'], 'resources': ['pods' if pods else 'configmaps']}],
         'failurePolicy': fail}
    if ns_selector is not None:
        h['namespaceSelector'] = ns_selector
    if obj_selector is not None:
        h['objectSelector'] = obj_selector
    if reinvoke is not None:
        h['reinvocationPolicy'] = reinvoke
    return h


def namespace(name, **labels):
    labels = dict(labels, **{'kubernetes.io/metadata.name': name})
    return {'kind': 'Namespace', 'metadata': {'name': name, 'labels': labels}}


CLUSTER = {'kind': 'List', 'items': [
    namespace('kyverno'), namespace('consul'), namespace('app'), namespace('kube-system'),
    webhook_config('MutatingWebhookConfiguration', 'consul-connect-injector',
                   [hook('consul-inject', 'consul', ns_selector={'matchExpressions': [{'key': 'kubernetes.io/metadata.name', 'operator': 'NotIn', 'values': ['kube-system']}]},
                         obj_selector={'matchExpressions': [{'key': 'app', 'operator': 'NotIn', 'values': ['consul']}]})]),
    webhook_config('ValidatingWebhookConfiguration', 'kyverno-resource-validating',
                   [hook('kyverno-validate', 'kyverno', ns_selector={'matchExpressions': [{'key': 'kubernetes.io/metadata.name', 'operator': 'NotIn', 'values': ['kube-system', 'kyverno']}]})]),
    webhook_config('MutatingWebhookConfiguration', 'admission-signer', [hook('signer', 'app', fail='Ignore', reinvoke='IfNeeded')]),
    webhook_config('MutatingWebhookConfiguration', 'image-digest', [hook('digest', 'app', fail='Ignore', reinvoke='IfNeeded')]),
    webhook_config('MutatingWebhookConfiguration', 'sidecar-injector', [hook('sidecar', 'app', fail='Ignore', reinvoke='IfNeeded')]),
    {'kind': 'HorizontalPodAutoscaler', 'metadata': {'name': 'web', 'namespace': 'app'},
     'spec': {'scaleTargetRef': {'kind': 'Deployment', 'name': 'web'},
              'metrics': [{'type': 'Resource', 'resource': {'name': 'cpu', 'target': {'type': 'Utilization', 'averageUtilization': 50}}}]}},
    {'kind': 'VerticalPodAutoscaler', 'metadata': {'name': 'web', 'namespace': 'app'},
     'spec': {'targetRef': {'kind': 'Deployment', 'name': 'web'}, 'updatePolicy': {'updateMode': 'Auto'}}},
]}

DESCRIPTION = {
    'facts': {'proxy': ['sidecar', []], 'pinned': ['digest', ['proxy']], 'signature': ['signer', ['pinned']]},
    'informers': [{'count': 2000, 'list_cost': 100.0}], 'capacity': 100.0, 'mean_watch': 450.0, 'history': 300.0,
    'surge': 30, 'running_pods': 16, 'free_slots': 0,
}


class Audit(unittest.TestCase):

    def setUp(self):
        self.report = sa.audit(CLUSTER, DESCRIPTION)

    def test_signal(self):
        sig = self.report['signal']
        self.assertEqual(len(sig), 1)
        self.assertEqual(sig[0]['workload'], 'app/Deployment/web')
        self.assertTrue(sig[0]['shared_metric'])
        self.assertAlmostEqual(sig[0]['ratio'], 1.581, places=3)

    def test_assumption_finds_the_cycle(self):
        a = self.report['assumption']
        self.assertEqual(a['cycles'], [['consul', 'kyverno']])
        self.assertAlmostEqual(a['ratio'], 1.0, places=6)
        self.assertIn('app', a['stranded'])

    def test_order_counts_the_passes(self):
        o = self.report['order']
        self.assertEqual(o['sequence'], ['signer', 'consul-inject', 'digest', 'sidecar'])
        self.assertEqual(o['passes'], 3)
        self.assertAlmostEqual(o['ratio'], 1.5)

    def test_state_and_time(self):
        self.assertAlmostEqual(self.report['state']['ratio'], 2000 * 100.0 / 100.0 / 750.0)
        self.assertAlmostEqual(self.report['time']['ratio'], 4.0)

    def test_fail_open_breaks_the_cycle(self):
        cluster = json.loads(json.dumps(CLUSTER))
        for item in cluster['items']:
            if item['metadata']['name'] == 'kyverno-resource-validating':
                item['webhooks'][0]['failurePolicy'] = 'Ignore'
        self.assertEqual(sa.audit(cluster, DESCRIPTION)['assumption']['cycles'], [])

    def test_malformed_input_is_reported(self):
        bad = {'kind': 'List', 'items': [{'kind': 'HorizontalPodAutoscaler', 'metadata': {'name': 'web'}, 'spec': {}}]}
        with self.assertRaises(sa.InputError) as ctx:
            sa.audit(bad, {})
        self.assertIn('HorizontalPodAutoscaler web', str(ctx.exception))
        self.assertIn('scaleTargetRef', str(ctx.exception))

    def test_description_missing_a_field_is_reported(self):
        with self.assertRaises(sa.InputError) as ctx:
            sa.audit(CLUSTER, {'informers': [{'count': 10}], 'capacity': 100.0})
        self.assertIn('list_cost', str(ctx.exception))

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            c, s = os.path.join(d, 'c.json'), os.path.join(d, 'd.json')
            json.dump(CLUSTER, open(c, 'w', encoding='utf-8'))
            json.dump(DESCRIPTION, open(s, 'w', encoding='utf-8'))
            out = subprocess.run([sys.executable, os.path.join(HERE, '..', 'audit', 'seam_audit.py'), c, '--description', s],
                                 capture_output=True, text=True, check=True).stdout
        self.assertIn('assumption', out)
        self.assertIn('binds', out)


if __name__ == '__main__':
    unittest.main()
