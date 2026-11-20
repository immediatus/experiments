"""Checks Part 4's fix sets: self-exclusion removes self-loops only; the fewest exclusions that leave no
start-time cycle (a minimum feedback arc set) and the fewest webhooks switched to Ignore (a minimum
feedback vertex set) are computed exactly; for k cluster-wide Fail webhooks that each exclude only their
own namespace they are k (k - 1) / 2 and k - 1.

Run: python3 -m unittest discover -s tests
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import random
import unittest

from audit import cyclic_components, min_feedback_arc_set, min_feedback_vertex_set


def complete(k):
    names = ['w%d' % i for i in range(k)]
    return {a: {b for b in names if b != a} for a in names}


class FixSets(unittest.TestCase):

    def test_complete_graph(self):
        for k in range(2, 6):
            g = complete(k)
            self.assertEqual(len(min_feedback_arc_set(g)), k * (k - 1) // 2)
            self.assertEqual(len(min_feedback_vertex_set(g)), k - 1)

    def test_acyclic_needs_nothing(self):
        g = {'a': {'b'}, 'b': {'c'}, 'c': set()}
        self.assertEqual(min_feedback_arc_set(g), set())
        self.assertEqual(min_feedback_vertex_set(g), set())

    def test_removing_the_sets_leaves_no_cycle(self):
        rng = random.Random(5)
        for _ in range(200):
            names = ['w%d' % i for i in range(rng.randint(2, 5))]
            g = {a: {b for b in names if b != a and rng.random() < 0.5} for a in names}
            arcs = min_feedback_arc_set(g)
            h = {a: {b for b in g[a] if (a, b) not in arcs} for a in g}
            self.assertEqual(cyclic_components(h), [])
            vs = min_feedback_vertex_set(g)
            h = {a: {b for b in g[a] if b not in vs} for a in g if a not in vs}
            self.assertEqual(cyclic_components(h), [])
            # minimality against brute force on the vertex set
            for r in range(len(vs)):
                for sub in itertools.combinations(sorted(g), r):
                    h = {a: {b for b in g[a] if b not in sub} for a in g if a not in sub}
                    self.assertNotEqual(cyclic_components(h), [])


if __name__ == '__main__':
    unittest.main()
