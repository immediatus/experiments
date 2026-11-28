"""Checks the exact restart statistics behind Part 4's table of random webhook clusters: k webhooks that fail
closed and exclude their own namespace, each matching another's pods with probability p. Enumerating every
graph with its probability replaces a sample. Two webhooks form a cycle only when each matches the other, so
the share is p squared exactly, and the enumeration agrees with the model's recovery and feedback-set searches
on every graph of three.

Run: python3 -m unittest discover -s tests
"""
import itertools
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from audit import cyclic_components, exact_restart_statistics, min_feedback_arc_set, min_feedback_vertex_set
from recovery import recover


class ExactRestart(unittest.TestCase):
    """Two webhooks form a cycle with probability p squared; enumeration agrees with the model on every graph of
    three."""

    def test_two_webhooks_form_a_cycle_with_probability_p_squared(self):
        for p in (0.5, 0.25):
            s = exact_restart_statistics(2, (p,))[p]
            self.assertAlmostEqual(s['cyclic'], p * p)
            self.assertAlmostEqual(s['stranded'], 2 * p * p)
            self.assertAlmostEqual(s['arcs'], p * p)
            self.assertAlmostEqual(s['vertices'], p * p)

    def test_enumeration_agrees_with_the_model_on_every_graph_of_three(self):
        names = ['w0', 'w1', 'w2']
        arcs = [(a, b) for a in names for b in names if a != b]
        p = 0.3
        tot = {'cyclic': 0.0, 'stranded': 0.0, 'arcs': 0.0, 'vertices': 0.0}
        for bits in itertools.product((0, 1), repeat=len(arcs)):
            g = {a: {b for (x, b), on in zip(arcs, bits) if on and x == a} for a in names}
            w = p ** sum(bits) * (1 - p) ** (len(arcs) - sum(bits))
            tot['cyclic'] += w * bool(cyclic_components(g))
            tot['stranded'] += w * len(recover({a: {i} for i, a in enumerate(names)}, g, set(range(3))))
            tot['arcs'] += w * len(min_feedback_arc_set(g))
            tot['vertices'] += w * len(min_feedback_vertex_set(g))
        s = exact_restart_statistics(3, (p,))[p]
        for key in tot:
            self.assertAlmostEqual(s[key], tot[key])


if __name__ == '__main__':
    unittest.main()
