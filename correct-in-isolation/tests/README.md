# tests/

Every test of the experiment, run by `python3 reproduce.py --check` before it compares the sections with the
frozen results, and by `python3 -m unittest discover -s tests` on their own. They check the model as well as its
ports: each closed form against the simulation, properties that must hold whatever the inputs, each documented
rule against its source, and the reader's audit tool against clusters whose verdict is known.

## Part 1, a shared signal

| File | What it checks |
|---|---|
| [`test_frontier_part1.py`](test_frontier_part1.py) | Checks Part 1's transition and frontier. |
| [`test_gc_data.py`](test_gc_data.py) | Pins the transcription of the cycle lower-bound overheads of Cai, Blackburn, Bond and Maas (ISPASS 2022, Table "Cycle LBOs averaged over 16 benchmarks"), the source Part 1 reads beta from for current collectors, and the elasticities taken from it. |
| [`test_history_law.py`](test_history_law.py) | Checks Part 1's history statistic. |
| [`test_model.py`](test_model.py) | Checks Part 1's model against properties it must have whatever its inputs: the relative gain array's rows and columns sum to one, a shared metric makes the gain matrix singular, the recommended split pairing has relative gain one without coupling, both loops leave total requested capacity at demand / target, and the closed forms agree with the simulation. |
| [`test_split_structure.py`](test_split_structure.py) | Checks Part 1's split pairing with the heap's structure made explicit. |
| [`test_supervisor.py`](test_supervisor.py) | Checks Part 1's autonomic supervisor: every supervisor_h hours it estimates q from the vertical loop's own histogram and sets the margin to 1 / (target q) - 1, at least zero. |
| [`test_tail_regimes.py`](test_tail_regimes.py) | Checks Part 1's gap: the vertical loop sizes from a percentile of per-pod samples, the horizontal loop holds the mean across pods. |
| [`test_tail_scope.py`](test_tail_scope.py) | Checks the scope of Part 1's tail regimes. |
| [`test_tolerance.py`](test_tolerance.py) | Per-direction horizontal tolerance (HPAConfigurableTolerance, GA in Kubernetes 1.37): a scale-up tolerance wide enough to swallow the vertical loop's step stops the staircase, and the width it needs is the step factor minus one. |
| [`test_transit.py`](test_transit.py) | Checks the signal seam in transit: the paired loops drifting at a 50% target, then a fix applied while the replica count is mid-staircase. |

## Part 2, a shared time scale

| File | What it checks |
|---|---|
| [`test_buffer.py`](test_buffer.py) | Checks Part 2's capacity buffer (the Cluster Autoscaler's CapacityBuffer API, beta since 1.35): a buffer sized as a percentage of the deployment's current replicas is held as fake pods the node loop provisions for, so it grows with every round and refills while the surge runs. |
| [`test_deadline.py`](test_deadline.py) | Checks Part 2's formal side over surges from 3x to 100x. |
| [`test_hazard.py`](test_hazard.py) | Checks the hazard rule for a memory kept as pods. |
| [`test_nested.py`](test_nested.py) | Checks Part 2's model: the nested time to capacity matches R tau_pod + (R - m) tau_node within the scan and sync latencies when headroom covers exactly m rounds, a node loop that sees the final need does no worse than one that sees only pending pods, and headroom covering every round removes every node wait. |
| [`test_node_tail.py`](test_node_tail.py) | Checks the lagged rule for a memory kept as nodes past the pod window's cap. |
| [`test_pod_memory.py`](test_pod_memory.py) | Checks the pod-memory extension of Part 2's model. |
| [`test_scale_down.py`](test_scale_down.py) | Checks the second-surge extension of Part 2's model: while the pod loop's stabilization window holds the surge's pods, a second surge is served at once; after it, the nodes the scale-down leaves behind act as headroom for the rounds placed before the node loop deletes them, so the time is R tau_pod + (R - m) tau_node with m those rounds; and, for a known gap, every unneeded-time between releasing at once and holding through the gap is dominated. |
| [`test_slots_frontier.py`](test_slots_frontier.py) | Checks Part 2's frontier in slots. |
| [`test_step_slots.py`](test_step_slots.py) | Checks the fewest free slots that remove c node waits from a nested surge (Part 2). |
| [`test_surge_tail.py`](test_surge_tail.py) | Checks Part 2's tail results. |
| [`test_tail_buffer.py`](test_tail_buffer.py) | Checks Part 2's buffer controller. |
| [`test_unknown_gap.py`](test_unknown_gap.py) | Checks the unknown-gap extension of Part 2's model. |

## Part 3, a shared state

| File | What it checks |
|---|---|
| [`test_bookmarks.py`](test_bookmarks.py) | Checks Part 3's bookmarks: without them a re-watch resumes from the last event its selector saw, so when every watch lasts at least the history it is answered 410 exactly when no event came in the last T_h seconds, with probability exp(-lam T_h); the list load this adds with no trigger at all is the forced backlog times that probability over the mean watch period. |
| [`test_history.py`](test_history.py) | Checks Part 3's history band: the watch cache keeps at least its event-fresh duration and, at a steady event rate, settles between that and four times it; a shorter history lowers every threshold, and at the specimen's list cost of 100 a history of 150 seconds sustains a storm where 300 seconds does not. |
| [`test_meanfield.py`](test_meanfield.py) | Checks the mean-field reading of Part 3's storm onset. |
| [`test_mixed.py`](test_mixed.py) | Checks Part 3's mixed informers: a list cost given per client reproduces the single-cost runs when every client has the same cost, under one queue and under fair queuing, and the per-client counts of re-watches answered 410 add up to the total. |
| [`test_relist.py`](test_relist.py) | Checks Part 3's model: each safeguard alone never re-lists beyond the trigger, the composite starts a second wave exactly past the closed-form threshold, no storm sustains itself below the necessary condition, and a sustained storm spends all capacity on LISTs. |
| [`test_relist_limited.py`](test_relist_limited.py) | Checks Part 3's model with the mechanisms the documented queue leaves to the implementation: the API server's queue wait limit (15 s, then 429) and the Reflector's backoff, with one FIFO queue and with APF fair queuing at the "system" level's defaults. |
| [`test_seats.py`](test_seats.py) | Checks Part 3's prices in seats. |
| [`test_split_controller.py`](test_split_controller.py) | Checks Part 3's formal side and its controller. |
| [`test_tail_lists.py`](test_tail_lists.py) | Checks Part 3's tail result. |
| [`test_waves.py`](test_waves.py) | Checks Part 3's rolling restart: a trigger in waves, each wave forcing a share of the informers to list at its own time (the informers that resume against one restarted server). |

## Part 4, a shared assumption

| File | What it checks |
|---|---|
| [`test_backoff.py`](test_backoff.py) | Checks Part 4's cold start through two documented backoffs: a ReplicaSet whose creations a webhook rejects retries at 5 ms (2^k - 1), so it next tries before twice the outage plus 5 ms; a container that crashes until a dependency is up restarts after 10, 20, 40 s and so on, capped at 300 s; and a chain through both is ready no earlier than with instant retries. |
| [`test_backoff_cap.py`](test_backoff_cap.py) | Checks Part 4's configurable kubelet backoff (KubeletCrashLoopBackOffMax, beta and on by default since Kubernetes 1.35: maxContainerRestartPeriod from 1 s to 300 s per node; the alpha ReduceDefaultCrashLoopBackOffDecay starts at 1 s and caps at 60 s): the cold-start chain with the default cap is unchanged, and a lower cap bounds how late the webhook can start, without making every case faster. |
| [`test_bypass.py`](test_bypass.py) | Checks Part 4's stuck eviction under the documented remedies: an operator who deletes the pod directly at each stall, as the eviction guide suggests, takes the drain to the same end as no budget at all; the unhealthy-pod eviction policy does not change the stall, because a rejected replacement is never a pod. |
| [`test_cycle_time.py`](test_cycle_time.py) | Checks Part 4's binding over time: a webhook that must be up to admit its own replacements binds when every replica is down at once; with one replica that is its first node failure, and with Z the mean time is close to 1 / (Z lam (lam w)^(Z - 1)) when lam w is small, checked against an event simulation at accelerated rates. |
| [`test_drain.py`](test_drain.py) | Checks the rolling-drain extension of the recovery model. |
| [`test_exact_restart.py`](test_exact_restart.py) | Checks the exact restart statistics behind Part 4's table of random webhook clusters: k webhooks that fail closed and exclude their own namespace, each matching another's pods with probability p. |
| [`test_fix_sets.py`](test_fix_sets.py) | Checks Part 4's fix sets: self-exclusion removes self-loops only; the fewest exclusions that leave no start-time cycle (a minimum feedback arc set) and the fewest webhooks switched to Ignore (a minimum feedback vertex set) are computed exactly; for k cluster-wide Fail webhooks that each exclude only their own namespace they are k (k - 1) / 2 and k - 1. |
| [`test_heartbeat.py`](test_heartbeat.py) | Checks Part 4's heartbeat model: a kubelet renews its Lease every 10 s and after a failure retries from 200 ms doubling to 7 s; behind a webhook that fails each call with probability q, the node is Unknown when no renewal succeeded in the last 50 s. |
| [`test_percolation.py`](test_percolation.py) | Checks Part 4's percolation results. |
| [`test_placement.py`](test_placement.py) | Checks Part 4's drain with replacements placed by the scheduler: the policy that puts every replacement where no later drain reaches it reproduces the frozen drain; a replacement placed on a node not yet drained is evicted again; spreading and packing lose at least as many application replicas as that policy over every drain order; and the documented practice loses nothing under any policy. |
| [`test_recovery.py`](test_recovery.py) | Checks Part 4's model: recovery stops exactly at start-time cycles inside the failed set, the per-component check passes on a cluster that never recovers, and the closed-form probability that a failure covers a cycle matches enumeration. |
| [`test_rollout.py`](test_rollout.py) | Checks Part 4's self-upgrade: a webhook that rejects its own pods rolls out a new version under the Deployment defaults (maxUnavailable 25% rounded down, maxSurge 25% rounded up); the old ReplicaSet is scaled down by maxUnavailable at once, every new pod is rejected, and the rollout stalls with n - floor(n / 4) replicas, which then last the harmonic number of that count times a node's mean time between failures. |

## Part 5, a shared order

| File | What it checks |
|---|---|
| [`test_admission.py`](test_admission.py) | Checks Part 5's model: commuting webhooks give one outcome in any order, an enabling chain of depth d reaches its fixed point from every order in d + 1 passes and not from the worst order in d, a conflicting pair has no common fixed point, the reinvocation pass calls only webhooks that opted in and saw a change, the closed-form share of converging orders matches enumeration, and a second admission's patches decide the fixed point where a comparison of the returned object misses an override. |
| [`test_builtins.py`](test_builtins.py) | Checks Part 5's built-in plugins: the in-tree mutating plugins run at the start of every pass, a second pass runs whenever a webhook changed the object in the first, and the count of Proposition 37 with every built-in placed first matches the simulation. |
| [`test_mixed_policy.py`](test_mixed_policy.py) | Checks Part 5's mixed reinvocation policies: a webhook whose configuration sets Never (the default, and what Istio, Linkerd, Vault and Gatekeeper ship) is called once, so in a chain of value links it must find its enabler's work already done when its single turn comes. |
| [`test_orchestrator.py`](test_orchestrator.py) | Checks Part 5's orchestrator. |
| [`test_order_match.py`](test_order_match.py) | Checks Part 5's match rules and its two cluster tests: a webhook skipped in the first round because it does not match is never called in a later one, so a link through a match rule is not repaired at any number of passes; the closed count of converging orders for chains with value and match links equals enumeration; a final round with no mutation certifies the admitted object for every webhook that was called, and only for those; a second admission of the admitted object mutates it exactly when it is not a common fixed point of the webhooks that match it. |
| [`test_patch_trail.py`](test_patch_trail.py) | Checks Part 5's patch trail and conflicts. |
| [`test_pinning.py`](test_pinning.py) | Checks Part 5's webhook that reads outside the object: a digest pin applied to each Pod as it is created resolves the tag at that moment, so a ReplicaSet whose pods are replaced at rate r while the tag moves at rate lam runs two images once a replacement follows a tag move: mean 1/lam + 1/r, and within a horizon H with probability 1 - (r e^{-lam H} - lam e^{-r H}) / (r - lam). |

## Part 6, every pair passes

| File | What it checks |
|---|---|
| [`test_audit.py`](test_audit.py) | Checks Part 6's whole-system tests: the n x n relative gain array has rows summing to one, a three-loop matrix whose every pair looks mild can be singular, the start-time cycle of three webhooks is found although every pair is acyclic, and the enabling depth matches the passes an admission chain needs. |
| [`test_cross_frontier.py`](test_cross_frontier.py) | Checks the cross-seam frontier of Part 6. |
| [`test_incomplete.py`](test_incomplete.py) | Checks Part 6's incomplete descriptions. |
| [`test_interaction_order.py`](test_interaction_order.py) | Checks Part 6's interaction-order law. |
| [`test_seam_audit.py`](test_seam_audit.py) | Checks the seam audit command, which reads a cluster's objects as `kubectl get ... -o json` prints them, and a description of what objects do not record, and runs the five whole-system tests of Part 6. |
| [`test_seam_ratio.py`](test_seam_ratio.py) | Checks Part 6's seam ratios: for each seam, what the composite asks over what it can give, so that the seam binds when the ratio passes one. |
| [`test_share_onset.py`](test_share_onset.py) | Checks that the storm onset scales with the list level's share of the server: the onset is a backlog, about 2,260 seconds of forced work, so a level with a fraction of the seats storms from that fraction of the whole server's onset list cost (Part 6, T110). |
| [`test_synthesis.py`](test_synthesis.py) | Checks Part 6's model: for the signal, assumption and order seams and every k from 3, a set of k mechanisms whose every proper subset passes the seam's test while the whole fails; the passes an order needs equal one plus the most inversions along any path of the facts the webhooks write, checked against simulation on random dependency graphs; and the order the API server derives from configuration names. |
| [`test_tolerance_surge.py`](test_tolerance_surge.py) | Checks Part 6's cross-seam reading of Part 1's two fixes: a target moved to the vertical loop's resting utilization and a scale-up tolerance that reaches it both stop the drift, but on Part 2's nested surge the tolerance keeps the 50% target's growth per round and costs about one round, while the moved target slows the surge several times over. |
| [`test_whole_supervisor.py`](test_whole_supervisor.py) | Checks Part 6's whole-system supervisor on the signal and time-scale seams, the pair that shares settings. |

## More than one part, and the model checkers

| File | What it checks |
|---|---|
| [`test_default_graph.py`](test_default_graph.py) | Checks the start-time graph built from shipped defaults (Parts 4 and 6). |
| [`test_memory.py`](test_memory.py) | Checks the hidden memory of Parts 1 and 3. |
| [`test_p.py`](test_p.py) | Checks the P models in p/ against their frozen verdicts, and the abstraction they rest on. |
| [`test_tla.py`](test_tla.py) | Checks the TLA+ specifications in tla/ against their frozen verdicts. |
| [`test_code_map.py`](test_code_map.py) | Checks that the experiment links every file of its code: each code folder has a README that links every file in it, and the experiment's README links each of those indexes. |
