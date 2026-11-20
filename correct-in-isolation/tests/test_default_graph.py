"""Checks the start-time graph built from shipped defaults (Parts 4 and 6). A component's pods need every
webhook that fails closed and whose default selectors match them; Kyverno (with a policy on Pods)
excludes kube-system and its own namespace, and Consul's injector excludes kube-system and a few
platform namespaces and skips its own pods by label. Together they form a cycle of two, and after a full
restart every component either one matches stays down, which is everything outside kube-system.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from audit import SURVEY_DEFAULTS, cyclic_components, default_start_graph
from recovery import recover


def full_restart(components):
    needs = default_start_graph(components)
    placement = {c: {c} for c in components}
    return needs, recover(placement, needs, set(components))


class DefaultGraph(unittest.TestCase):

    def test_kyverno_and_consul_form_a_cycle(self):
        needs = default_start_graph(SURVEY_DEFAULTS)
        self.assertEqual([set(c) for c in cyclic_components(needs)], [{'consul', 'kyverno'}])

    def test_full_restart_strands_everything_they_match(self):
        needs, down = full_restart(SURVEY_DEFAULTS)
        self.assertNotIn('coredns', down)
        # both webhooks exclude kube-system, so what runs there recovers, and nothing else does
        self.assertEqual(down, {c for c, d in SURVEY_DEFAULTS.items() if d['ns'] != 'kube-system'})

    def test_either_alone_recovers(self):
        for gone in ('consul', 'kyverno'):
            comps = {k: v for k, v in SURVEY_DEFAULTS.items() if k != gone}
            self.assertEqual(full_restart(comps)[1], set())

    def test_one_exclusion_breaks_the_cycle(self):
        comps = dict(SURVEY_DEFAULTS)
        consul = dict(comps['consul'])
        consul['excludes'] = consul['excludes'] | {'kyverno'}
        comps['consul'] = consul
        self.assertEqual(full_restart(comps)[1], set())


if __name__ == '__main__':
    unittest.main()


class BreakingTheCycle(unittest.TestCase):
    """Part 6's assumption x order frontier: three settings each break the Kyverno and Consul cycle, and each
    leaves a different set of pods outside one webhook's writes."""

    def test_kyverno_excluding_consul_breaks_the_cycle(self):
        comps = dict(SURVEY_DEFAULTS)
        comps['kyverno'] = dict(comps['kyverno'], excludes=comps['kyverno']['excludes'] | {'consul'})
        needs, down = full_restart(comps)
        self.assertEqual(cyclic_components(needs), [])
        self.assertEqual(down, set())
        self.assertNotIn('kyverno', default_start_graph(comps)['consul'])
