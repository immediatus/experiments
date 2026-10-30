# Sections of `reproduce.py`

Every number the series quotes is printed by one section of `reproduce.py`. Run one with
`python3 reproduce.py T12`, all of them with `python3 reproduce.py`, and compare everything
with the frozen output with `python3 reproduce.py --check`. Which claim each section supports
is in [CLAIMS.md](CLAIMS.md).

| Section | What it shows |
|---|---|
| T1 | The one-line ratio rule fed a replica count that is 0, 1, 2 or 3 sync periods old |
| T2 | Saturated CPU metric: rounds, time to capacity, overshoot and backlog for 3x to 300x overloads |
| T3 | The same with a metric that does not saturate |
| T4 | Growth factor per round for different targets and limits |
| T5 | Three scaling signals under timeouts, retries and wasted work |
| T6 | Fixed capacity after a spike: predicted recovery time against the fluid model and a request-level simulation |
| T7 | A demand-only signal at different targets and retry policies; work lost in seconds of each run's own stepped demand |
| T8 | The same load with an admission bound |
| T9 | Pareto-distributed overloads: recovery time, backlog and rejected volume |
| T10 | Saturated pods serving less than their nominal rate |
| T11 | Backlog loop, idealized: the standing delay needed to stop hunting, as a function of window over dead time |
| T12 | Backlog loop through the ported controller: sixteen observed boundaries against that curve |
| T13 | The same loop under demand noise, consumer-rebalance pauses and slower polling |
| T14 | Long windows: whether a standing delay of e dead times still holds |
| T15 | The one-line ratio rule with a stale replica count: exact and sufficient stability bounds |
| T16 | Fixed capacity with a retry budget: predicted recovery time against the fluid model |
| T17 | A replica ceiling close to the amplified load: recovery time against the margin |
| T18 | The pods ordered and counted ready at each change after a 3x, 10x and 30x step (the staircase figure) |
| T19 | Predictions for the cluster run: four pods at a 50% target with a ceiling of 50 |
| T20 | One sync of the ported calculation, showing that pods not yet ready cap the recommendation |
| T21 | The hottest target that can size a k-fold overload within R rounds, checked against the simulation |
| T22 | Targets at which a saturated reading falls inside the tolerance band, so the controller never scales |
| T23 | The tolerance band ending a round early at a 63% target |
| T24 | Pods every minute over the last hour of a backlog-scaled loop, hunting and settled |
| T25 | The backlog loop at the Kafka default threshold, with and without a stabilization window |
| T26 | The idealized backlog loop at a standing delay of e dead times: no overshoot at any window |
| T27 | The idealized backlog loop with no window and with a very short one |
| T28 | One sync of the ported external per-pod calculation, ordering past pods already on order |
| T29 | Sweeps of both ported calculations: CPU recommendation against pods on order, backlog recommendation against backlog |
| T30 | Request-level runs with no trigger: healthy at A x rho up to 2.85 |
| T31 | Trap predictions sized to the cluster kit: fixed 4 pods, fivefold 300-second spike |
| T32 | Anatomy of the trap: pods, good work and wasted work each 30 seconds, for the first-attempt and ingress scalers |
| T33 | Retry amplification and threshold 1/A for three retry stacks |
| T34 | Peak backlog against overload: local growth exponent and backlog over overload times rounds |
| T35 | Admission-bound sweep under Pareto overloads (index 1.5) with retries: backlog and loss quantiles, tail indices |
| T36 | Cluster-sized predictions for the admission bound and the replica-ceiling floor |
| T37 | Approximations to the curve Phi(w): harmonic-balance closed form, long-window values, the asymptotic form toward e, the roots near e |
| T38 | Server farms with setup times: exact mean response times (Gandhi, Harchol-Balter and Adan 2010) against the request-level simulator |
| T39 | Queue-consumer predictions sized to the cluster kit: 5 to 20 pods needed, ceiling 100, standing delays and windows of Part 2's criteria |
| T40 | Signal predictions sized to the cluster kit: first-attempt, ingress and paired scalers under a sustained fivefold step with retries |
| T41 | Admission bounds above and below the timeout, sized to the cluster kit: peak pods, demand lost, abandoned work served |
| T42 | A metric that does not saturate, sized to the cluster kit: CPU limit four times the request |
| T43 | The admission-bound sweep either side of the timeout, 12 and 8 seconds |
| T44 | The T39 predictions for the last hour of a 5 h run, the length of the cluster suite's queue runs: the same ranges as at 20 h |
| T45 | Proposition 7 against the fluid model: the long-spike form and the full form for twelve spikes across retries, budgets and the cluster kit |
| T46 | Peak pods after a step: round arithmetic against the simulated peak, 3x to 300x |
| T47 | One step of the cluster-sized queue consumer at the Kafka default threshold, every 30 s: pods ordered, pods consuming, backlog |
| T48 | Every signal and lever of Parts 3 and 4 on common axes: pods held per pod of demand against first-attempt work lost |
| T49 | Hill estimates of the tail index with 90% bootstrap intervals, as the share of the sample treated as the tail varies |

Losses are reported in seconds of the stepped demand, which does not depend on the length
of a run. A state that never recovers is reported as ongoing or stuck.
