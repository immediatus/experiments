# audit/

[`seam_audit.py`](seam_audit.py) runs the five whole-system tests of Part 6 on a cluster's own objects. It reads
files and never talks to a cluster, and it needs nothing beyond Python's standard library.

```bash
kubectl get mutatingwebhookconfigurations,validatingwebhookconfigurations,namespaces,hpa,vpa -A -o json > cluster.json
python3 audit/seam_audit.py cluster.json --description description.json   # the description is optional
python3 audit/seam_audit.py cluster.json --json                            # the report as JSON
```

The exit status is 0 for a report and 2 for input the tool cannot read; the message names the file and the
missing field.

## The example

[`example-cluster.json`](example-cluster.json) and [`example-description.json`](example-description.json) are
the inputs [`../tests/test_seam_audit.py`](../tests/test_seam_audit.py) checks, so the example below is the
tested one. The cluster holds Kyverno and Consul's injector at their shipped defaults, three mutating webhooks
whose names put a chain out of order, and a deployment with both autoscalers on one CPU metric.

```
$ python3 audit/seam_audit.py audit/example-cluster.json --description audit/example-description.json
signal      app/Deployment/web           ratio 1.581  binds  (target 0.50 on cpu, with a vertical autoscaler)
time scale  ratio 4.000  binds  (4 rounds, 0 covered)
state       ratio 2.667  binds  (2000 informers)
assumption  ratio 1.000  binds  cycles [['consul', 'kyverno']]; stranded by a full restart: app, consul, kyverno
order       ratio 1.500  binds  (3 passes; order signer, consul-inject, digest, sidecar)
```

Each ratio is the seam ratio of Definition 21: a seam binds when its ratio passes one, and the assumption binds
at one, since a single start-time cycle has a spectral radius of exactly one.

## What the objects give

| Seam | Read from | Assumed where the objects are silent |
|---|---|---|
| Signal | each workload's HorizontalPodAutoscaler metrics and VerticalPodAutoscaler | the vertical autoscaler at its documented defaults |
| Assumption | every webhook configuration's rules, selectors and failure policy, matched against the namespaces | a webhook with an object selector skips its own pods and matches every other component's |
| Order | the mutating configurations' names, sorted, and each webhook's reinvocation policy | no facts unless the description gives them, so one pass and a verdict that can only err toward *holds* |

## The description

The description adds what no object records. A time-scale or state test whose fields are all absent is reported
as not tested. A state test given only part of its fields is an input error, exit status 2, naming the missing field.

| Field | Type | Meaning | Test |
|---|---|---|---|
| `facts` | `{fact: [writer, [facts it needs]]}` | each fact a mutating webhook writes, the webhook that writes it, and the facts it needs first | order |
| `informers` | `[{"count": n, "list_cost": seat-seconds}]` | groups of informers and the server work of one list each | state |
| `capacity` | seat-seconds per second | the server's capacity for lists | state |
| `mean_watch` | seconds | the mean length of a watch | state |
| `history` | seconds | the history the watch cache keeps | state |
| `surge` | multiple of the demand | the largest surge to plan for | time scale |
| `running_pods` | pods | the pods running before the surge, 16 if absent | time scale |
| `free_slots` | pods | free pod slots held in advance, 0 if absent | time scale |

The state test needs `informers`, `capacity`, `mean_watch` and `history` together; the time scale needs
`surge`, and uses the lowest CPU utilization target among the HorizontalPodAutoscalers, 0.5 if there is none.

## How far to trust it

By Proposition 40 a description that leaves out a need, a prerequisite or an informer can hide an assumption,
order or state failure but never invent one, so a verdict of *binds* on those seams stands. A coupling the
description leaves out can move the signal's verdict either way, so measure the couplings before trusting a
*holds* there. Edges no object records, such as a component's need for cluster DNS, have to be asked of their
owners.
