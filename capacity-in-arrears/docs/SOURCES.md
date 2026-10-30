# Source reading record: Kubernetes HPA

Tag v1.34.0, paths under `pkg/controller/podautoscaler/` unless a full path is shown
(`apis/...` is `pkg/apis/...`). Every statement the series makes about the controller maps to one row.
The last column says whether the identical line exists at tag v1.30.0.

| Claim | File | Function | Line | Source line | Same in v1.30.0 |
|---|---|---|---|---|---|
| Replica count is computed from ready pods only | replica_calculator.go | GetResourceReplicas | 118 | `return int32(math.Ceil(usageRatio * float64(readyPodCount)))` | yes |
| Tolerance check returns the current count unchanged | replica_calculator.go | GetResourceReplicas | 112 | `if tolerances.isWithin(usageRatio) {` | NO |
| Unready pods count as 0 usage on scale-up | replica_calculator.go | GetResourceReplicas | 132 | `metrics[podName] = metricsclient.PodMetric{Value: 0}` | yes |
| Scale-up with unready pods is a separate branch | replica_calculator.go | GetResourceReplicas | 110 | `scaleUpWithUnready := len(unreadyPods) > 0 && usageRatio > 1.0` | yes |
| Missing metrics count as full request (or target) on scale-down | replica_calculator.go | GetResourceReplicas | 125 | `fallbackUtilization := int64(max(100, targetUtilization))` | yes |
| Hold if the recomputed ratio would flip direction | replica_calculator.go | GetResourceReplicas | 150 | `if tolerances.isWithin(newUsageRatio) \|\| (usageRatio < 1.0 && newUsageRatio > 1.0) \|\| (usageRatio > 1.0 && newUsageRatio < 1.0) {` | NO |
| Recomputed count uses every pod that entered the calculation | replica_calculator.go | GetResourceReplicas | 156 | `newReplicas := int32(math.Ceil(newUsageRatio * float64(len(metrics))))` | yes |
| Pending pods are grouped as unready | replica_calculator.go | groupPods | 419 | `if pod.Status.Phase == v1.PodPending {` | yes |
| During the CPU initialization period a pod is unready until one metric window after its ready transition | replica_calculator.go | groupPods | 439 | `unready = condition.Status == v1.ConditionFalse \|\| metric.Timestamp.Before(condition.LastTransitionTime.Time.Add(metric.Window))` | yes |
| After that period a pod is unready only if it has never been ready | replica_calculator.go | groupPods | 442 | `unready = condition.Status == v1.ConditionFalse && pod.Status.StartTime.Add(delayOfInitialReadinessStatus).After(condition.LastTransitionTime.Time)` | yes |
| Utilization is an integer percentage (truncated) | metrics/utilization.go | GetResourceUtilizationRatio | 49 | `currentUtilization = int32((metricsTotal * 100) / requestsTotal)` | yes |
| Tolerance band definition | replica_calculator.go | isWithin | 57 | `return (1.0-t.scaleDown) <= usageRatio && usageRatio <= (1.0+t.scaleUp)` | NO |
| Downscale stabilization takes the maximum recent recommendation | horizontal.go | stabilizeRecommendation | 972 | `} else if rec.recommendation > maxRecommendation {` | yes |
| Scale-up limit max(2 x current, 4) | horizontal.go | calculateScaleUpLimit | 1285 | `return int32(math.Max(scaleUpLimitFactor*float64(currentReplicas), scaleUpLimitMinimum))` | yes |
| Scale-up limit constants | horizontal.go | (package constants) | 62 | `scaleUpLimitFactor  = 2.0` | yes |
| External per-pod metric: ceil(usage / target per pod) | replica_calculator.go | GetExternalPerPodMetricReplicas | 392 | `replicaCountResult := math.Ceil(float64(usage) / float64(targetUsagePerPod))` | NO |
| External value metric scales the ready pod count | replica_calculator.go | getUsageRatioReplicaCount | 293 | `replicaCount = int32(math.Ceil(usageRatio * float64(readyPodCount)))` | yes |
| Default sync period 15 s | config/v1alpha1/defaults.go | RecommendedDefaultHPAControllerConfiguration | 41 | `obj.HorizontalPodAutoscalerSyncPeriod = metav1.Duration{Duration: 15 * time.Second}` | yes |
| Default downscale stabilization 5 min | config/v1alpha1/defaults.go | RecommendedDefaultHPAControllerConfiguration | 44 | `obj.HorizontalPodAutoscalerDownscaleStabilizationWindow = metav1.Duration{Duration: 5 * time.Minute}` | yes |
| Default CPU initialization period 5 min | config/v1alpha1/defaults.go | RecommendedDefaultHPAControllerConfiguration | 47 | `obj.HorizontalPodAutoscalerCPUInitializationPeriod = metav1.Duration{Duration: 5 * time.Minute}` | yes |
| Default initial readiness delay 30 s | config/v1alpha1/defaults.go | RecommendedDefaultHPAControllerConfiguration | 50 | `obj.HorizontalPodAutoscalerInitialReadinessDelay = metav1.Duration{Duration: 30 * time.Second}` | yes |
| Default tolerance 0.1 | config/v1alpha1/defaults.go | RecommendedDefaultHPAControllerConfiguration | 53 | `obj.HorizontalPodAutoscalerTolerance = 0.1` | yes |
| Default scale-up policy: 100% or 4 pods per 15 s, no stabilization | apis/autoscaling/v2/defaults.go | (package variables) | 29 | `scaleUpLimitPercent         int32 = 100` | yes |
| Per-HPA tolerance behind a feature gate | horizontal.go | tolerancesForHpa | 1445 | `allowConfigurableTolerances := utilfeature.DefaultFeatureGate.Enabled(features.HPAConfigurableTolerance)` | NO |

## Differences at v1.30.0

Five recorded lines are worded differently at v1.30.0. All five concern how the tolerance is
expressed, not what the calculation does:

- v1.30.0 has one symmetric tolerance held on the calculator and tested as
  `math.Abs(1.0-usageRatio) <= c.tolerance`. v1.34.0 has a `Tolerances` struct with separate
  scale-up and scale-down values, tested by `isWithin`, and a feature gate
  (`HPAConfigurableTolerance`) that lets one HPA override them.
- The direction-flip hold and the external per-pod rule exist at v1.30.0 with the same
  logic; only the tolerance expression inside them differs.

The ready-only ratio, the unready-as-zero rule, the pending-pod grouping, the CPU
initialization rule, integer truncation, the stabilization maximum, the scale-up limit and
all six controller defaults are identical at both tags. These statements therefore hold
for v1.30.0 through v1.34.0; line numbers are for v1.34.0.

## History, from the pull requests themselves

- kubernetes/kubernetes #33593, "HPA: Consider unready pods separately", merged
  2016-11-08. Its description gives the purpose in its own words: "pods frequently use
  extra CPU during initialization, so we want to consider them separately", and the
  effect: "unready pods cause the autoscaler to be a bit more conservative ... in
  anticipation of the new pods later becoming ready and handling load." It also states
  the rules ported here: unready pods count as 0 CPU when scaling up and are ignored when
  scaling down; a recomputation "cannot change the direction of the scale."
- #67252, "Fix HPA sample sanitization", merged 2018-08-24, and #68068, "Change CPU
  sample sanitization in HPA", merged 2018-08-31. They introduce the initialization
  period and the rule that a ready pod's sample is ignored until a full metric window
  has been collected since its transition. #67252 describes the failure it fixes: pods
  that burn CPU while initializing trigger a scale-up, and their own start-up usage then
  triggers another "even though existing pods can handle work".

What this supports: the stated purpose was start-up CPU noise and
anticipation of capacity already ordered. It does not support the claim that the maintainers
judged the documented formula unstable under delay; no description says that.

## What the documentation says (kubernetes/website, main, read 2026-10-08)

File `content/en/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale.md`, section
"Algorithm details".

- It opens: "From the most basic perspective, the HorizontalPodAutoscaler controller
  operates on the ratio between desired metric value and current metric value", followed
  by `desiredReplicas = ceil[currentReplicas x (currentMetricValue / desiredMetricValue)]`.
- Below the formula it describes the adjustments in prose: pods "set aside" when not yet
  ready or when their latest CPU sample predates readiness; missing metrics assumed at
  100% of the desired value on scale-down and 0% on scale-up; not-yet-ready pods assumed
  at 0% on scale-up; no action if the recalculated ratio "reverses the scale direction,
  or is within the tolerance".
- It states that the base ratio is calculated "using the remaining pods not set aside".
  It does not restate the formula with the ready-pod count in place of `currentReplicas`;
  the source does (`math.Ceil(usageRatio * float64(readyPodCount))`).
- It notes that "the original value for the average utilization is reported back via the
  HorizontalPodAutoscaler status, without factoring in the not-yet-ready pods or missing
  metrics, even when the new usage ratio is used". The status therefore shows a number
  the decision did not use.
- Defaults stated there: tolerance 0.1, initial readiness delay 30 seconds, CPU
  initialization period 5 minutes, downscale stabilization 5 minutes.

What this supports: the one-line formula is the documented summary and is what is
commonly quoted; the calculation as run differs from it in the ways the same page
describes. What it does not support: that the documentation is wrong or hides the behaviour.

## Default target

`pkg/apis/autoscaling/annotations.go` line 34 at v1.34.0: `const DefaultCPUUtilization = 80`,
with the comment "the default value for CPU utilization, provided no other metrics are
present". `pkg/apis/autoscaling/v2/defaults.go` line 77 applies it when an HPA specifies no
metrics. This supports saying the API's default target is 80% CPU utilization. It does not support
calling 80% an industry standard; no source read here says that.

## KEDA (documentation v2.19, kedacore/keda-docs, read 2026-10-09)

Used by the backlog study. Each line is from the named page of the documentation.

| Fact | Page | Wording or value |
|---|---|---|
| KEDA scales from 1 to N through the HPA | concepts/scaling-deployments, "Activating and Scaling thresholds" | "it is the HPA controller who takes the scaling decisions based on the configuration defined in the generated HPA" |
| KEDA itself decides only 0 to 1 and back | same page | the activation phase "only applies to 0<->1 scaling" |
| Polling interval | reference/scaledobject-spec, `pollingInterval` | default 30 seconds; from 1 to N "the HPA will also poll regularly for metrics", by default every 15 seconds |
| Metric caching | concepts/scaling-deployments, "Caching Metrics" | off by default; without it the metrics server "by default queries the scaler" on each HPA request |
| Cooldown | reference/scaledobject-spec, `cooldownPeriod` | default 300 seconds, and it "only applies when scaling to 0" |
| Replica ceiling | reference/scaledobject-spec, `maxReplicaCount` | default 100 |
| Scaling behaviour | reference/scaledobject-spec, `horizontalPodAutoscalerConfig.behavior` | passed "directly to the HPA's `behavior` field" |
| Metric type | reference/scaledobject-spec, `scalingModifiers.metricType` | `AverageValue` by default |
| Kafka lag threshold | scalers/apache-kafka, `lagThreshold` | "Target value for the total lag (sum of all partition lags)"; default 10 |
| Kafka replica cap | scalers/apache-kafka, notice | by default replicas do not exceed the number of partitions |
| SQS queue length | scalers/aws-sqs, `queueLength` | default 5; counts visible plus in-flight messages by default |
| RabbitMQ trigger modes | scalers/rabbitmq-queue, "Choosing the right trigger mode" | `QueueLength` "to keep number of messages in the queue at selected, nominal level"; `MessageRate` "to keep the consumption rate up to messages publication rate" |

With an `AverageValue` external metric the ported controller computes
`ceil(metric / target per pod)` (`GetExternalPerPodMetricReplicas`), which is the rule the
backlog study runs.
