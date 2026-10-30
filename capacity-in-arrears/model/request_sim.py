"""Request-level check of the trap condition (the fluid model has no randomness).

M/M/c queue, FIFO, Poisson arrivals, exponential service. A request waiting `timeout` s
is abandoned: its client retries at once (up to R times) and the abandoned copy stays in
the queue and is still served. Fixed capacity. A spike of factor k lasts D seconds.
Recovery = time after the spike of the last timeout, compared in reproduce.py with
Proposition 7 (formulas.py), which predicts permanent failure when (R+1)*rho >= 1.
"""
import heapq
import random
from collections import deque


def simulate(rho, R, seed, c=20, mu=5.0, k=10.0, D=300.0, timeout=10.0, start=60.0, horizon=20000.0):
    """One run of c servers of rate mu at utilization rho, with a k-fold spike from `start`
    lasting D seconds and R retries after a `timeout`. Deterministic for a given seed.

    Returns (time of the last timeout after the spike, or None if there was none; number of
    timeouts in the whole run).
    """
    rng = random.Random(seed)
    cap = c * mu
    lam0 = rho * cap
    lam_max = lam0 * k
    # A request is [arrival, attempt, state]. State 0 waiting; 1 abandoned by its client but
    # still queued; 2 in service for a waiting client; 3 in service after its client left.
    queue = deque()
    watch = deque()          # same objects, in arrival order, for timeouts
    busy = 0
    done = []                # service completion times
    t = 0.0
    next_arr = rng.expovariate(lam_max)
    last_timeout = None
    n_timeout = 0

    def admit(now, attempt):
        nonlocal busy
        req = [now, attempt, 0]
        if busy < c:
            busy += 1
            req[2] = 2
            heapq.heappush(done, now + rng.expovariate(mu))
        else:
            queue.append(req)
            watch.append(req)

    while True:
        t_done = done[0] if done else float('inf')
        t_out = watch[0][0] + timeout if watch else float('inf')
        t = min(next_arr, t_done, t_out)
        if t > horizon:
            break
        if t == t_out:
            req = watch.popleft()
            if req[2] == 0:
                req[2] = 1
                n_timeout += 1
                if t > start + D:
                    last_timeout = t
                if req[1] < R:
                    admit(t, req[1] + 1)
        elif t == t_done:
            heapq.heappop(done)
            if queue:
                req = queue.popleft()
                was = req[2]
                req[2] = 2 if was == 0 else 3
                heapq.heappush(done, t + rng.expovariate(mu))
            else:
                busy -= 1
        else:
            rate = lam0 * (k if start <= t < start + D else 1.0)
            if rng.random() < rate / lam_max:
                admit(t, 0)
            next_arr = t + rng.expovariate(lam_max)
    return last_timeout, n_timeout
