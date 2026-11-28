# Part 4: The Guarantee Nobody Breaks

Companion to [The Guarantee Nobody Breaks](https://e-mindset.space/blog/correct-in-isolation-part4-the-guarantee-nobody-breaks/).
The post states the argument; this page shows where each number comes from and how to change the inputs.
Layer tags follow the series: **Bound** (proof or source), **Fit** (reading or approximation), **Estimate**
(simulation).

## The question

When admission webhooks, DNS and the workloads they serve each guarantee their behavior only while the others
run, when does the cluster fail to recover, why can no check of one component see it, and what does ordinary
maintenance do to a webhook that rejects its own pods?

## The belief

Every component passes its own checks, so the cluster recovers from any failure each component can survive.

## The mechanism, as the code runs it

[`model/recovery.py`](../model/recovery.py) has two parts. `recover` runs recovery to its fixpoint after a set of
nodes fails, with availability edges: a webhook with failurePolicy Fail must be up to admit a pod. `rolling_drain`
drains the nodes one at a time, as a rolling upgrade does, and separates availability edges from rejection edges, a
running webhook's rules rejecting the pod, which the documentation says deny "regardless of the failurePolicy
setting". It honours disruption budgets as the Eviction API does.

## The laws

- **Bound. Proposition 23.** Recovery stops exactly at components on or downstream of a cycle of availability edges
  among components that lost every replica (T13); the topological core is an earlier post's Proposition 66.
- **Bound. Proposition 24.** Random failures cover a cycle on $Z$ of $Q$ nodes with probability
  $\binom{Q-Z}{K-Z}/\binom{Q}{K}$ (T14).
- **Bound. Every guarantee holds, vacuously.** Every component's conditional guarantee holds on the trace in which nothing in the cycle
  starts (checked by the tests on every failure set).
- **Bound. Proposition 25.** A webhook that rejects its own pods never replaces a lost replica while it runs; one
  rolling drain removes it under Fail, leaves one replica under Ignore, and stalls after $n_w - a_w$ evictions with a
  budget (T47). What the drain takes from the application depends on the drain order (T49).
- **Bound. Corollary 4.** Such a webhook lasts, on average, the harmonic number of its replicas times a node's mean time
  between failures (T48).
- **Bound. Ignore fixes half.** Failure policy Ignore removes availability edges and leaves rejection edges (T47).
- **Estimate. A webhook in every heartbeat.** A webhook that fails closed and matches Lease updates turns nodes
  unknown in spells; one that fails nine calls in ten evicts more nodes than one that fails them all (T62). Failed
  calls that wait out a ten-second timeout leave four renewals per grace period, and full-rate evictions start at a
  failure rate of 0.7, against 0.9 when a failure costs nothing (T114).

## The gap and the intervention

- **Bound. Vacuous guarantees and Abadi and Lamport.** Each guarantee holds; circular reasoning from them is sound for
  safety, and recovery is liveness.
- **Bound. Proposition 26.** In a large random start-time graph a giant stranded core appears where the mean
  product of in- and out-degree passes the mean degree; hubs move that point toward zero (T100).
- **Bound. A relaxation set.** Relaxing the edges into a feedback vertex set frees the core; a greedy controller
  frees all of it with a set small beside what it frees, and leaves it stranded when a few edges are missing
  from its graph or cannot be relaxed ([`model/percolation.py`](../model/percolation.py), T101).
- **Estimate. A relaxation is a cliff.** Prefixes of the relaxation free almost nothing until it is complete (T104).

## The results

Every claim, with its section, is in [CLAIMS.md](CLAIMS.md).

## The bill, and when the advice reverses

A webhook that strands the cluster on every full restart whatever its spread. One rolling upgrade that removes a webhook rejecting its own pods, or stops at a stuck eviction if it has a budget, which the documented remedy then completes. With packing, an application that loses all of its replicas in most upgrades. A webhook that cannot roll out its own next version and keeps fewer replicas than it was given. Cluster-wide webhooks that each exclude their own namespace and still strand one another on a full restart. After an outage, a way back up to 2.95 times as long as the outage made necessary at the default restart cap, 1.90 times at a cap of 60 seconds.

**When the advice reverses.** The advice of this post is to find every start-time edge and remove the ones that can bind. It reverses where the check a webhook performs matters more than the cluster's recovery, as for a security control that must not be bypassed during an outage. There an availability edge is the point, and the price is an out-of-band recovery path, planned in advance.

## What you can vary

`recover` takes any placement and any availability edges; `rolling_drain` takes the placement, availability and
rejection edges, the drain order and disruption budgets; `simulated_life` and `drain_order_losses` take their counts
and seeds. The closed forms are in [`model/formulas.py`](../model/formulas.py): `bind_probability`, `rejection_life`,
`app_loss_distribution`. The assumptions are in [ASSUMPTIONS.md](ASSUMPTIONS.md).

## Where the replacements go

`placed_drain` in [`model/recovery.py`](../model/recovery.py) places each replacement as the scheduler would:
out of reach of later drains (which is `rolling_drain`), spread to the node with fewest pods (the default), or
packed onto the one with most. Section T58 runs 20000 drain orders under each, with and without a surge node.

![Application replicas lost to one rolling upgrade, by placement policy](../figures/placement.svg)

*What one rolling upgrade takes from an application whose pods need a webhook that rejects its own. With replacements out of reach of later drains, or spread by the default scorer, the loss is graded. Packed by the most-allocated scorer, the replicas gather on one node not yet drained, and the application keeps all three or loses all three.*

## The stuck eviction and the way back

`rolling_drain(..., bypass=True)` applies the eviction guide's remedy, deleting the pod at each refused eviction
(T59). `workqueue_retry_after`, `kubelet_start_after` and `cold_start_chain` in [`model/formulas.py`](../model/formulas.py)
compose the two documented backoffs on a full restart (T60).

![Seconds until the application is ready after a full restart, against seconds until DNS is ready](../figures/cold-start.svg)

*The way back through two backoffs. With instant retries the application follows DNS by a fixed 100 seconds. With the kubelet's restart backoff and the workqueue's retry backoff it climbs in steps, past twice that time and nearly three times at worst, and its ratio to it falls back only where the caps of 300 and 1000 seconds bind.*
