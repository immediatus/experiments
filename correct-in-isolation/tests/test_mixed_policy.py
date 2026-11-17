"""Checks Part 5's mixed reinvocation policies: a webhook whose configuration sets Never (the default,
and what Istio, Linkerd, Vault and Gatekeeper ship) is called once, so in a chain of value links it
must find its enabler's work already done when its single turn comes. With every member IfNeeded the
chain behaves as Proposition 28 says; marking a member Never is equivalent, for convergence, to
turning its incoming link into a match link.

Run: python3 -m unittest discover -s tests
"""
import os
import sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import itertools
import unittest

from admission import admit, chain, pod, typed_chain


def converged_share(webhooks, passes=2):
    full = admit(pod(), webhooks, passes=len(webhooks) + 2)
    orders = list(itertools.permutations(webhooks))
    return sum(admit(pod(), list(o), passes=passes) == full for o in orders) / len(orders)


def with_never(webhooks, positions):
    for i in positions:
        webhooks[i].never = True
    return webhooks


class MixedPolicy(unittest.TestCase):

    def test_all_ifneeded_is_unchanged(self):
        self.assertAlmostEqual(converged_share(chain(2)), 5 / 6)

    def test_a_never_member_is_called_once(self):
        ws = with_never(chain(1), [1])
        # dependent before its enabler: called once, before the enabler acts, never again
        out = admit(pod(), [ws[1], ws[0]], passes=2)
        self.assertNotIn('level1', {k for k, _ in out[2]})

    def test_never_equals_a_match_link_for_convergence(self):
        for n in (3, 4, 5):
            for j in range(1, n):
                kinds = ['value'] * (n - 1)
                kinds[j - 1] = 'match'
                for passes in (2, 3):
                    a = converged_share(with_never(chain(n - 1), [j]), passes)
                    b = converged_share(typed_chain(kinds), passes)
                    self.assertAlmostEqual(a, b, msg=(n, j, passes))

    def test_never_on_the_first_member_costs_nothing(self):
        self.assertAlmostEqual(converged_share(with_never(chain(3), [0])), converged_share(chain(3)))


if __name__ == '__main__':
    unittest.main()


class ClosedForm(unittest.TestCase):

    def test_two_pass_share_matches_enumeration(self):
        from formulas import never_share
        for n in (2, 3, 4, 5):
            for eta in range(n):
                ws = with_never(chain(n - 1), [eta] if eta else [])
                self.assertAlmostEqual(never_share(n, eta), converged_share(ws), msg=(n, eta))

    def test_reduces_to_the_earlier_shares(self):
        import math
        from formulas import converged_share as eulerian_share, never_share
        for n in (2, 3, 4, 5, 6):
            self.assertAlmostEqual(never_share(n, 0), eulerian_share(n, 2))
            self.assertAlmostEqual(never_share(n, n - 1), 1 / math.factorial(n))


class SurveyMix(unittest.TestCase):

    def test_mix_share_bounds(self):
        from formulas import converged_share as eulerian_share, mix_share, never_share
        for n in (2, 3, 4, 5):
            self.assertAlmostEqual(mix_share(n, 0.0), eulerian_share(n, 2))
            self.assertAlmostEqual(mix_share(n, 1.0), never_share(n, n - 1))
            self.assertLess(mix_share(n, 10 / 13), mix_share(n, 0.0) + 1e-12)

    def test_mix_share_by_enumeration(self):
        import itertools
        from formulas import mix_share, never_share
        n, q = 4, 0.3
        total = 0.0
        for flags in itertools.product((0, 1), repeat=n - 1):
            prob = 1.0
            for f in flags:
                prob *= q if f else 1 - q
            eta = max([i + 1 for i, f in enumerate(flags) if f], default=0)
            total += prob * never_share(n, eta)
        self.assertAlmostEqual(mix_share(n, q), total)
