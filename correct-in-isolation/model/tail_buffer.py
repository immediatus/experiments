"""A buffer controller for Part 2. Surges arrive with sizes Pareto above kmin = l / u (the surge that just
saturates the running pods). Before each surge the controller holds slots that cover c rounds,
n0 (g^c - 1); the surge costs those slots for the mean gap plus `price` slot-seconds per pod-second short
in its ramp (formulas.ramp_shortfall). The cover before a surge depends only on earlier surges, so the
mean of cover_cost over the covers held, 'expected_cost', is the policy's expected cost per surge, free of
the sample's own tail; 'mean_cost' is the cost the sample happened to realise. After the surge it reads the surge's size, capped at `cap` when
the replica count is capped by maxReplicas, and sets c for the next surge by its rule:

  'oracle'  the optimal cover for the true exponent (formulas.optimal_cover), held throughout;
  'fixed'   start_c, held throughout;
  'peak'    the rounds that cover the largest surge read so far;
  'mle'     the optimal cover for the maximum-likelihood exponent of the readings so far, read as
            censored at `cap` when fix is set and as exact otherwise, capped at max_c (the buffer's
            limits); with an exponent at or below 1 no finite cover exists, and c goes to max_c.
"""
import math
import random

from formulas import cover_cost, optimal_cover, pareto_mle, ramp_shortfall


def run(alpha, rule='mle', surges=200, seed=1, n0=16, price=100.0, mean_gap=3600.0, tau_pod=90, tau_node=210,
        cap=None, fix=True, start_c=0, max_c=8, kmin=2.0, warm=5, target=0.5, limit=1.0):
    g = limit / target
    rng = random.Random(seed)
    c = optimal_cover(alpha, price, mean_gap, tau_node, g)[1] if rule == 'oracle' else start_c
    if c is None:
        c = max_c
    readings, sizes, covers, costs, a = [], [], [], [], None
    for _ in range(surges):
        k = kmin * (1.0 - rng.random()) ** (-1.0 / alpha)
        sizes.append(k)
        covers.append(c)
        costs.append(mean_gap * n0 * (g ** c - 1.0) + price * ramp_shortfall(k, n0, tau_pod, tau_node, c, target, limit))
        readings.append(min(k, cap) if cap else k)
        if rule == 'peak':
            c = max(c, math.ceil(math.log(max(readings) / kmin) / math.log(g) - 1e-9))
        elif rule == 'mle' and len(readings) >= warm:
            a = pareto_mle(readings, kmin, cap if (cap and fix) else None)
            best = optimal_cover(a, price, mean_gap, tau_node, g)[1]
            c = max_c if best is None else min(best, max_c)
    expected = math.fsum(cover_cost(x, alpha, n0, price, mean_gap, tau_pod, tau_node, g) for x in covers)
    return {'final_c': c, 'covers': covers, 'sizes': sizes, 'mean_cost': math.fsum(costs) / len(costs),
            'costs': costs, 'expected_cost': expected / len(covers), 'alpha_hat': a}
