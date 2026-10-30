# Assumptions

Facts about Kubernetes come from the source at tag v1.34.0 and are recorded line by line
in `SOURCES.md`. Everything below is a modelling assumption. Each one is listed with the
result it could change.

## The port (`hpa_port.py`)

| Assumption | Could change |
|---|---|
| Only the default path is ported: no `behavior` block on the autoscaler | Results under custom scale-up or scale-down policies |
| All pods have equal requests and none is missing metrics, failed, or being deleted | Nothing in the sections here; those branches of the controller are not exercised |
| The initialization rule is modelled as "ready one metric window after the pod starts serving" | The length of a round by up to the difference between that and a real pod's readiness timing |

## The loop model (`loop_sim.py`)

| Assumption | Could change |
|---|---|
| Fluid queue, 1 s steps, one service, identical pods | Fine-grained timing; nothing that depends on rounds of 90 s or more |
| A new pod serves 90 s after it is created (the dead time) and counts as ready one 30 s metric window later | Every time in T2, T4, T5, T8 and T10 scales with these two numbers; overshoot ratios do not |
| The CPU metric is the mean usage over the last 30 s | The alignment of rounds with the 15 s sync by up to one sync period |
| First in, first out service | The trap of T5 to T7. Serving the newest request first, or dropping requests past a deadline, weakens it |
| A client that times out retries at once; `backoff` delays retries without removing them | Timing of the trap, not its condition (T7) |
| The server still spends the work for a request whose client has gone | The trap of T5 to T7. This is the worst case; cancelling abandoned work removes the wasted work |
| A rejected request costs no CPU | T8. If rejection is expensive, admission control relieves less |
| A saturated pod serves its full nominal rate unless `eta` is set below 1 | T2 and T4 are best cases; T10 shows the effect of `eta` |
| Scale-down removes pods at once, pending pods first | How fast over-provision is released; not time to capacity |

## The request-level check (`request_sim.py`)

| Assumption | Could change |
|---|---|
| Poisson arrivals, exponential service times, 20 servers | Scatter around the recovery times of T6. Heavy-tailed service times are not tested |
| Fixed capacity | Nothing in T6, which is a fixed-capacity statement by design |

## The overload study (`tail_study.py`)

| Assumption | Could change |
|---|---|
| The overload factor is Pareto with a minimum of 1.5, capped at 2,000, applied as a sustained step | The quantiles of T9. The tail estimate over 3,000 trials describes the sampled range, not the asymptote |

## The backlog loop (`backlog_ideal.py`, `backlog_sim.py`, `backlog_boundary.py`)

| Assumption | Could change |
|---|---|
| Fluid backlog: it grows at the demand rate and shrinks at one pod's rate times the ready pods | Fine-grained timing; not the boundary, which is a property of the delays |
| A new pod consumes one dead time after it is created; removing a pod takes effect at once | The asymmetry the result rests on. If removal were also delayed, that delay adds to the window's |
| The idealized model has no sampling, rounding, tolerance, floor or ceiling | Nothing in T11 and T14, which are about that model. T12 measures how far the ported loop departs from it |
| The ported loop reads the backlog every 15 s and acts at the 15 s sync | About 10 s of extra delay on each branch (T12) |
| "Hunting" means pods swing by more than 30% of the needed count in the last hour of a 20-hour run | Where the boundary is drawn, by a few seconds. Shorter runs misread slow decay as hunting |
| Demand noise is a lognormal factor redrawn every 60 s plus Poisson-like arrivals | The noise columns of T13 only |
| A consumer-group rebalance stops all consumption for a fixed pause after any change in consuming pods | The rebalance columns of T13 only. This is a crude model of a rebalance and its result is preliminary |
| No cap on replicas by partition count, no activation from zero, no metric caching | Not tested |

## What no file here establishes

Behaviour on a real cluster. The kit in `cluster/` exists to test that, and its service
and load generator have been exercised on local sockets only.
