"""Checks Part 1's split pairing with the heap's structure made explicit. Garbage collection costs CPU as a
function of the heap over the live set it traces, rho = H / L, with elasticity -beta. The heap is sized from the
memory limit, which the vertical loop keeps in ratio to the request. The live set follows per-pod load with
share theta_live; the memory the vertical loop observes follows it with share theta, and follows the request with
elasticity xi, a heap that grows into its limit. Then

    G = [[-(1 + beta theta_live), -beta], [-theta, -(1 - xi)]]
    lambda_11 = (1 + beta theta_live)(1 - xi) / ((1 + beta theta_live)(1 - xi) - beta theta)

The earlier form 1/(1 - beta theta) is the case of a live set that does not follow load and a heap that does not
grow with its limit.

Run: python3 -m unittest discover -s tests
"""
import math
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]

import unittest

from audit import relative_gains
from formulas import coupled_relative_gain, critical_xi, split_gain_matrix, split_relative_gain


def structural_outputs(log_n, log_r, beta, theta, theta_live, xi):
    """log u_cpu and log u_mem of one pod from the structure, at demand 1: per-pod work w = 1/N; CPU use is work
    times a collection factor rho^-beta with rho = r / L and L = w^theta_live; observed memory is w^theta r^xi."""
    w = math.exp(-log_n)
    rho = math.exp(log_r) / w ** theta_live
    cpu = w * rho ** -beta
    mem = w ** theta * math.exp(log_r) ** xi
    return math.log(cpu), math.log(mem) - log_r


class Structure(unittest.TestCase):

    def test_matrix_is_the_jacobian(self):
        h = 1e-6
        for beta, theta, tl, xi in ((1.28, 1.0, 1.0, 0.0), (0.58, 0.5, 0.2, 0.3), (0.6, 1.0, 0.0, 0.7)):
            base = structural_outputs(0.0, 0.0, beta, theta, tl, xi)
            dn = structural_outputs(h, 0.0, beta, theta, tl, xi)
            dr = structural_outputs(0.0, h, beta, theta, tl, xi)
            jac = [[(dn[i] - base[i]) / h, (dr[i] - base[i]) / h] for i in range(2)]
            g = split_gain_matrix(beta, theta, tl, xi)
            for i in range(2):
                for j in range(2):
                    self.assertAlmostEqual(jac[i][j], g[i][j], places=4)
            self.assertAlmostEqual(relative_gains(g)[0][0], split_relative_gain(beta, theta, tl, xi), places=9)

    def test_earlier_form_is_a_special_case(self):
        for beta, theta in ((1.28, 1.0), (0.58, 0.5), (0.31, 1.0)):
            self.assertAlmostEqual(split_relative_gain(beta, theta), coupled_relative_gain(beta, theta), places=12)

    def test_live_set_that_follows_load_cancels_the_coupling(self):
        self.assertAlmostEqual(split_relative_gain(1.28, 1.0, 1.0, 0.0), 2.28, places=12)

    def test_heap_growing_into_its_limit_is_singular_at_the_critical_xi(self):
        e = critical_xi(1.28, 1.0, 1.0)
        self.assertAlmostEqual(e, 1.0 / 2.28, places=12)
        g = split_gain_matrix(1.28, 1.0, 1.0, e)
        self.assertAlmostEqual(g[0][0] * g[1][1] - g[0][1] * g[1][0], 0.0, places=12)
        self.assertLess(split_relative_gain(1.28, 1.0, 1.0, e + 0.05), 0.0)


if __name__ == '__main__':
    unittest.main()
