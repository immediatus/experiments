# Falsification Criteria

Each part of the series ends with observations on a real cluster that would refute it.
They are predictions: the series was published without running them, and nothing here
claims they have been confirmed. Anyone with the hardware can run them with
[`cluster/run_suite.py`](../cluster/run_suite.py) and report the outcome, refutations
included, as [Reporting a run](#reporting-a-run) describes.

## Status

| Criterion | Part | What it tests | Predictions from | Status |
|---|---|---|---|---|
| P1-F1 | 1 | The same first request for 3x and 5x steps | T19 | predicted, not yet run |
| P1-F2 | 1 | At most one growth factor per round | T19 | predicted, not yet run |
| P1-F3 | 1 | The ceiling causes the overshoot | T42 | predicted, not yet run |
| P1-F4 | 1 | The dead band at a 93% target | T22 | predicted, not yet run |
| P2-F1 | 2 | The hunting boundary exists | T39, T44 | predicted, not yet run |
| P2-F2 | 2 | The window raises the boundary | T39, T44 | predicted, not yet run |
| P2-F3 | 2 | Removing the window does not rescue the default | T39, T44 | predicted, not yet run |
| P3-F1 | 3 | A trigger is required | T30 | predicted, not yet run |
| P3-F2 | 3 | The threshold $A\rho = 1$ | T31 | predicted, not yet run |
| P3-F3 | 3 | The signal decides | T40 | predicted, not yet run |
| P3-F4 | 3 | Pairing restores recovery | T40 | predicted, not yet run |
| P4-F1 | 4 | The bound removes the overshoot and the loss | T36 | predicted, not yet run |
| P4-F2 | 4 | The ceiling floor | T36 | predicted, not yet run |
| P4-F3 | 4 | The bound must be shorter than the timeout | T41 | predicted, not yet run |

A status changes only with a reported run: `as predicted`, `not as predicted`, or `REFUTED`,
with a link to the report. A refuted claim is rewritten in the post, not softened.

## How to run them

The suite needs a kind cluster with metrics-server and KEDA 2.19, set up as the header of
[`cluster/kit.py`](../cluster/kit.py) describes, on a node of at least 16 cores. Then:

```bash
export NODE=<the kind node's address>
python3 cluster/run_suite.py list                  # 22 runs, about 56 hours
python3 cluster/run_suite.py run calibrate         # first: measures the dead time and the round
python3 cluster/run_suite.py all                   # every criterion, one run at a time
python3 cluster/run_suite.py verdict               # judge the saved runs again
```

Calibration comes first because every prediction assumes a 90-second dead time and a
120-second round. If the cluster measures more than 15 s and 20 s away from those, `all`
stops: the predictions must be regenerated for the measured values before a verdict means
anything. Each run gets its own namespace, deleted and waited out before the next starts, and
saves `runs/<run>/` with the recorder's and load generator's CSV files.

## The criteria

### One Bit per Dead Time

The runs use a 16-core node, pods requesting and limited to 250 millicores, four pods at a 50%
target before the step and a replica ceiling of 50.

**P1-F1, the same first request.** Two load steps, 3x and 5x, both large enough to saturate
the metric. *Prediction:* both order 7 pods, then 8 within one sync, then 14 and 16 one round
later. *Refuted if:* the orders differ before the 3x run's capacity meets its load.

**P1-F2, at most one factor per round.** The same steps, timed to the moment serving capacity
meets the load. *Prediction:* 105 s for 3x and 225 s for 5x, one round apart, with peaks of 16
and 32 pods against 12 and 20 needed. *Refuted if:* the ready count rises faster than twice
per round, or the 5x run meets its load in the same round as the 3x run.

**P1-F3, the ceiling causes the overshoot.** The 5x step with the CPU limit at 1,000
millicores, four times the request. *Prediction:* the count rises to the 20 pods needed and no
further, and capacity meets the load at the step. *Refuted if:* the overshoot persists with a
metric that does not saturate.

**P1-F4, the dead band.** A 3x step at a 93% target with the limit at the request.
*Prediction:* no scale-up for as long as the step lasts. *Refuted if:* the controller adds
pods.

### The Delay a Window Demands

A broker generates demand stepping from 50 to 200 messages a second; each consumer takes 10 a
second after a 90-second start delay, so 20 pods are needed under a ceiling of 100. The post's
predictions are for the last hour of a twenty-hour run (T39). The suite's queue runs last five
hours, and for the last hour of a five-hour run the model gives the same ranges (T44).

**P2-F1, the boundary exists.** The default 300-second window, standing delays of 60 and 150
seconds, below and above the predicted boundary of about 90. *Prediction:* 6 to 35 pods at 60
seconds, 19 to 21 at 150. *Refuted if:* the loop settles well below the boundary or hunts well
above it.

**P2-F2, the window raises the boundary.** A 60-second standing delay with a 60-second and a
300-second window. *Prediction:* rests between 19 and 22 pods with the short window, hunts
between 6 and 35 with the long one. *Refuted if:* the longer window settles the loop the
shorter one could not.

**P2-F3, removing the window does not rescue the default.** The Kafka default of ten messages
per pod, with and without the window. *Prediction:* both hunt from one pod to the ceiling of
100. *Refuted if:* removing the window alone brings the loop to rest.

### Demand Is Not Debt

A service that keeps working on abandoned requests, a load generator with a ten-second timeout
and two retries, and a meter that publishes first-attempt and ingress rates for KEDA.

**P3-F1, a trigger is required.** 50% utilization, steady load for three hours, no spike.
*Prediction:* no timeouts. *Refuted if:* the service falls into the failed state without a
trigger.

**P3-F2, the threshold.** Four pods held fixed, a fivefold spike for 300 seconds at 30% and at
40% utilization. *Prediction:* recovery after about 9,756 s at 30%; none at 40%. *Refuted
if:* the 40% run recovers, or the 30% run does not.

**P3-F3, the signal decides.** Autoscaled on first attempts and on ingress, at a 50% target,
under a sustained fivefold step. *Prediction:* first attempts stay failed at 20 pods and lose
99.3% of demand; ingress climbs to the ceiling of 50, recovers 270 s after the step and settles
at 20. *Refuted if:* the first-attempt run recovers without a change in amplification, or the
ingress run stays failed.

**P3-F4, pairing restores recovery.** Both signals on one autoscaler. *Prediction:* recovery
after 270 s, and 4 pods with no step, as with the clean signal alone. *Refuted if:* the paired
run stays failed, or holds more pods than the clean signal in steady state.

### The Barrier the Scaler Cannot Hold

Four pods at a 50% target, a ten-second timeout and two retries.

**P4-F1, the bound removes the overshoot and the loss.** A sustained fivefold step on CPU with
a ceiling of 50, with and without a 5-second admission bound. *Prediction:* without, 50 pods
and 10.3% lost; with, 21 pods and 1.2%. *Refuted if:* the bounded run still reaches the
ceiling, or loses as much.

**P4-F2, the ceiling floor.** A fivefold 300-second spike with ceilings of 6, 7 and 12; the
amplified load needs six pods. *Prediction:* 6 never recovers; 7 after about 6,974 s; 12 after
about 1,085 s. *Refuted if:* 6 recovers, or recovery does not fall roughly as one over the
margin.

**P4-F3, the bound must be shorter than the timeout.** The P4-F1 step with a 20-second bound and
a 5-second one. *Prediction:* the 20-second run still serves abandoned work, reaches 50 pods
and loses 7.5%; the 5-second run serves none, peaks at 21 and loses 1.2%. *Refuted if:* the
20-second bound removes the abandoned work as completely.

## Reporting a run

Open an issue with the repository's
[falsification-run template](../../.github/ISSUE_TEMPLATE/falsification-run.md) and include:

- the verdict line for the criterion from `runs/verdicts.txt`;
- the calibration: `runs/cluster.json` and the `calibrate` verdict, with the measured dead
  time and round;
- the environment: node cores and memory, kind and Kubernetes versions, KEDA version,
  container runtime;
- for every run the criterion uses, `runs/<run>/` (`exp.yaml`, `hpa.csv`, `load.csv`,
  `meta.json`), attached or linked as an archive.

A refuted criterion changes its status here to `REFUTED`, with a link to the issue.
