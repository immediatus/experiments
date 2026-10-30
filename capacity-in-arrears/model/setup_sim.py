"""Request-level check against exact results for server farms with setup times.

Gandhi, Harchol-Balter and Adan (2010), "Server farms with setup costs", Performance Evaluation 67(11):
M/M/k with Poisson arrivals (rate lam), exponential job sizes (rate mu), exponential setup (rate alpha),
one central first-come-first-served queue. A server is on (serving), off, or in setup; servers turn off
as soon as they have nothing to serve.

  ON/OFF/STAG : at most one server in setup at a time. Theorem 1: T = I + T_{M/M/k} in distribution,
                so E[T] = 1/alpha + E[T_{M/M/k}].
  ON/OFF(inf) : every job not being served has its own server in setup (k unbounded). Theorem 2: the
                limiting probabilities factor as pi(i, j) proportional to rho^i / i! * prod_{l=1}^{j-i}
                lam / (lam + l alpha), with i jobs being served and j jobs in the system.

Standard library only. Deterministic for a given seed.
"""
import heapq
import math
import random
from collections import deque


def erlang_c_mean_response(lam, mu, k):
    """Mean response time of M/M/k (ON/IDLE): 1/mu + C(k, a) / (k mu - lam)."""
    a = lam / mu
    s = math.fsum(a ** n / math.factorial(n) for n in range(k))
    last = a ** k / math.factorial(k) * (k / (k - a))
    c = last / (s + last)
    return 1 / mu + c / (k * mu - lam)


def onoff_inf_mean_response(lam, mu, alpha, mmax=5000):
    """Mean response time of ON/OFF(inf) from Theorem 2 and Little's law: jobs in service ~ Poisson(rho),
    independent of the number M waiting for their setup, P(M = m) proportional to prod_{l<=m} lam/(lam+l alpha)."""
    rho = lam / mu
    w = [1.0]
    for m in range(1, mmax):
        w.append(w[-1] * lam / (lam + m * alpha))
    em = math.fsum(m * x for m, x in enumerate(w)) / math.fsum(w)
    return (rho + em) / lam


def simulate(lam, mu, alpha, k, stag, seed, jobs=300000, warm=30000):
    """Mean response time by event simulation. stag=True: at most one server in setup. k=None: unbounded."""
    rng = random.Random(seed)
    events = [(rng.expovariate(lam), 0, 0.0)]           # (time, kind, payload)
    queue = deque()                                     # arrival times of jobs not in service, FIFO
    busy = 0
    pending = set()                                     # ids of setups in progress
    next_id = 0
    done = 0
    acc = 0.0
    n_acc = 0

    def start_setups(t):
        nonlocal next_id
        while len(pending) < len(queue):
            if k is not None and busy + len(pending) >= k:
                return
            if stag and len(pending) >= 1:
                return
            next_id += 1
            pending.add(next_id)
            heapq.heappush(events, (t + rng.expovariate(alpha), 1, float(next_id)))

    def cancel_extra():
        while len(pending) > len(queue):
            pending.discard(max(pending))               # memoryless setups: which one is cancelled does not matter

    def serve(t):
        nonlocal busy
        arr = queue.popleft()
        busy += 1
        heapq.heappush(events, (t + rng.expovariate(mu), 2, arr))

    while done < jobs:
        t, kind, pay = heapq.heappop(events)
        if kind == 0:
            queue.append(t)
            heapq.heappush(events, (t + rng.expovariate(lam), 0, 0.0))
        elif kind == 1:
            if int(pay) not in pending:
                continue
            pending.discard(int(pay))
            if queue:
                serve(t)
        else:
            busy -= 1
            done += 1
            if done > warm:
                acc += t - pay
                n_acc += 1
            if queue:
                serve(t)
        cancel_extra()
        start_setups(t)
    return acc / n_acc
