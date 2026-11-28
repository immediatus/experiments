# Sections of `reproduce.py`

Every number the series quotes is printed by one section of `reproduce.py`. Run one with
`python3 reproduce.py T12`, all of them with `python3 reproduce.py`, and compare everything
with the frozen output with `python3 reproduce.py --check`. Which claim each section supports
is in [CLAIMS.md](CLAIMS.md). Sections are numbered in the order they were frozen; the part each
belongs to is given below, and Parts 5 and 6 have their sections frozen ahead of their posts.

| Section | What it shows |
|---|---|
| T1 | Part 1: a shared signal. Relative gain of the horizontal loop |
| T2 | Part 1: a shared signal. Horizontal targets with an equilibrium (margin 0.15, tolerance 0.1; vertical tolerance 0 for a steady load, 0.1 the documented threshold) |
| T3 | Part 1: a shared signal. Drift below the band (target 0.5, steady demand 100 cores, 10 replicas, documented recommender) |
| T4 | Part 1: a shared signal. Long-run replica doubling time below the band, steady demand (400 days) |
| T5 | Part 1: a shared signal. Coupling from published garbage-collection cost (heap multiple 2, 3, 5) |
| T19 | Part 1: a shared signal. Horizontal loop on a custom metric, vertical loop on CPU |
| T20 | Part 1: a shared signal. Vertical margin at which a shared-metric pairing rests (tolerance 0.1; vertical tolerance 0 and 0.1) |
| T21 | Part 1: a shared signal. Long-run replica doubling under the documented vertical update rule (200 days) |
| T22 | Part 1: a shared signal. Targets near the band at q 1.0 (narrow band from 0.791, widened from 0.719), 200 days |
| T23 | Part 1: a shared signal. The drift as a staircase (target 0.5 and 0.6, steady demand) |
| T24 | Part 1: a shared signal. The staircase law at other recommender settings (target 0.5, steady demand, request floor lowered to 0.001 cores so each staircase runs long enough to measure, warm-up 2.5 step intervals, 300 days) |
| T39 | Part 1: a shared signal. Coupling from current collectors (OpenJDK 17, cycle lower-bound overheads, geometric mean of 16 benchmarks, ISPASS 2022; heap as a multiple of the minimum; beta from neighboring two-decimal table values) |
| T6 | Part 2: a shared time scale. Pod loop nested in node loop, no headroom (n0 16, target 0.5, limit = request, 8 pods per node, pod 90 s, node 210 s) |
| T7 | Part 2: a shared time scale. Node provisioning time, k 30 |
| T8 | Part 2: a shared time scale. Headroom held in advance (n0 64, one pod per node, so slots are exact), and every slot count swept for the bands just short of a step that are slower than the step below |
| T9 | Part 2: a shared time scale. Node size as hidden headroom, k 30, n0 16 |
| T25 | Part 2: a shared time scale. The headroom penalty across timing (k 30, n0 64, one pod per node; 0, 53 and 56 free slots) |
| T26 | Part 2: a shared time scale. Where the headroom penalty appears (n0 64, one pod per node, pod 90 s, node 210 s) |
| T27 | Part 2: a shared time scale. The horizontal target sets the number of node waits (k 30, n0 16, pod 90 s, node 210 s, no free slots at the start) |
| T28 | Part 2: a shared time scale. A second 30x surge after the first is scaled down (n0 16, 8 pods per node, pod 90 s, node 210 s, HPA stabilization 300 s, CA unneeded time 600 s) |
| T29 | Part 2: a shared time scale. The unneeded time against a known gap of 1200 s (as T28, instant deletion) |
| T30 | Part 2: a shared time scale. Exponential gaps between 30x surges (as T28, instant deletion; 200 gaps at the quantiles for the simulated means) |
| T31 | Part 2: a shared time scale. The worst gap (as T28, 58 spare nodes) |
| T32 | Part 2: a shared time scale. Break-even holding when the ramp outlasts the pod loop's window (58 spare nodes, pod 90 s, node 210 s, stabilization 300 s) |
| T33 | Part 2: a shared time scale. The same 900 s memory kept by nodes or by pods (as T28, instant deletion) |
| T34 | Part 2: a shared time scale. Memoryless gaps, the memory kept as pods first up to the 3600 s cap, then as nodes |
| T35 | Part 2: a shared time scale. Holding pods for the break-even time against the worst gap (58 spare nodes, unneeded 0 s; the window cap of 3600 s is reached at rate 174.0) |
| T36 | Part 2: a shared time scale. The hazard rule, memory kept as pods (Weibull gaps, mean 1800 s, 58 spare nodes, cold time 1200 s, window capped at 3600 s) |
| T37 | Part 2: a shared time scale. Expected cost against the window, as a multiple of releasing at once (as T36, exchange rate 64) |
| T38 | Part 2: a shared time scale. The hazard rule against the simulation (shape 0.5, mean 1800 s, exchange rate 64, 300 gaps at the quantiles, instant deletion, unneeded 0 s) |
| T40 | Part 2: a shared time scale. Memory kept as nodes past the one-hour pod window (Weibull gaps, 58 spare nodes, window 3600 s; forever stands for an unneeded time of 200000 s) |
| T10 | Part 3: shared state. Informers re-listing behind a queued API server (2000 clients, capacity 100 seat-s/s, history 300 s, watch 300 to 600 s, every client forced to LIST at t 0) |
| T11 | Part 3: shared state. Does the trigger reach the failed state (LISTs still running in hour 8) |
| T12 | Part 3: shared state. Each safeguard alone, LIST cost 100, and both together in the idealized queue and with the documented wait limit |
| T41 | Part 3: shared state. The queue with its wait limit (as T10; 15 s wait limit then 429, Reflector backoff; fair queuing at the system level) |
| T42 | Part 3: shared state. Where the second wave starts with the wait limit (pulse, 3 hours) |
| T43 | Part 3: shared state. Does the trigger decide the storm (LISTs in hour 8; trigger spread 0, 450, 900, 1800 s) |
| T44 | Part 3: shared state. Partial triggers (a fraction of clients forced to LIST at t 0; LISTs in hour 8) |
| T45 | Part 3: shared state. Consecutive rejections behind a re-watch answered 410 (history 300 s) |
| T46 | Part 3: shared state. Why the onset is sharp (wait limit, one queue, pulse trigger; attempts after the first hour) |
| T57 | Part 3: a shared state. How much history a watch through the watch cache has at a steady event rate, and the thresholds and storm onset with 300, 150 and 75 seconds of history |
| T65 | Part 3: a shared state. Pages of a paginated list that fit within the history when every page waits the full wait limit |
| T66 | Part 3: a shared state. How long a storm lasts near its onset, over 72 hours and ten seeds |
| T67 | Part 3: a shared state. The storm onset when the informers' priority level gets a share of the server |
| T68 | Part 3: a shared state. Informers of mixed sizes with the specimen's total forced work, one queue and fair queuing |
| T69 | Part 3: a shared state. How long the second wave lasts below the storm, and the square-root slowing near the onset |
| T70 | Part 3: a shared state. Re-watches and steady list load with no bookmarks and no trigger |
| T13 | Part 4: a shared assumption. Share of failures after which something never comes back (9 nodes, 3 zones; DNS 2 replicas, app 3) |
| T14 | Part 4: a shared assumption. Probability that k random node failures cover a start-time cycle on u distinct nodes |
| T47 | Part 4: a shared assumption. A rolling node upgrade, every node drained once in order, under availability and rejection edges, with and without a disruption budget |
| T48 | Part 4: a shared assumption. The life of a webhook that rejects its own pods, node failures independent, a lost replica never replaced |
| T49 | Part 4: a shared assumption. Application replicas lost to one rolling drain, over drain orders (webhook rejects its own pods, failurePolicy Fail; 3 webhook and 3 application replicas, each on its own node; 20000 random orders) |
| T58 | Part 4: a shared assumption. Where the scheduler puts replacements during a rolling drain: out of reach, spread, packed, with and without a surge node |
| T59 | Part 4: a shared assumption. The documented remedy for a stuck eviction, deleting the pod directly, applied to the drain of T47 |
| T60 | Part 4: a shared assumption. A full restart through the workqueue's and the kubelet's documented backoffs, against instant retries |
| T61 | Part 4: a shared assumption. Mean time until a webhook that must admit its own replacements binds, with independent node failures and the documented eviction toleration |
| T62 | Part 4: a shared assumption. A Fail webhook matching Lease updates and failing each call with probability q: Unknown time, five-minute spells and the node controller's eviction regime |
| T63 | Part 4: a shared assumption. A webhook that rejects its own pods rolls out a new version of itself under the Deployment defaults |
| T64 | Part 4: a shared assumption. Fail webhooks that each exclude their own namespace: cycles, stranding after a full restart, and the fewest fixes, exact over every graph |
| T15 | Part 5: a shared order. Mutating webhooks over every order (1 pass: the weaker reading; 2: the reinvocation contract; 3: beyond it) |
| T16 | Part 5: a shared order. Enabling chain of n webhooks (depth n - 1), all IfNeeded |
| T50 | Part 5: a shared order. A link through a match rule, over every order; a webhook skipped in round 0 is never called later |
| T51 | Part 5: a shared order. Chains with value and match links, all IfNeeded, every order equally likely |
| T52 | Part 5: a shared order. The two cluster checks under the contract: a clean last pass in the audit trail, and a second admission, read by its patches and by the object it returns, with an override added as a seventh scenario |
| T71 | Part 5: a shared order. Istio's and Vault's injectors at chart defaults, ordered by configuration name |
| T72 | Part 5: a shared order. A mutating admission policy and a webhook with a value link, in the current plugin order and in the contract's worst case |
| T73 | Part 6: the whole. How often a failure of a random system is one that a check of every pair passes, for the signal, assumption and order seams |
| T74 | Part 6: the whole. Fixing the signal seam through the horizontal target or through the metric, and what each does to the time-scale seam |
| T75 | Part 6: the whole. The default priority levels: heartbeats kept apart from kubelet lists, and the storm onset in the lists' level |
| T76 | Part 5: a shared order. Built-in mutating plugins run first in every pass: the 2018 case, and chains that end in a built-in |
| T77 | Part 5: a shared order. A digest pin applied to each Pod: time until one ReplicaSet runs two images |
| T17 | Part 6: the whole. Every pair passes, the whole fails |
| T18 | Part 6: the whole. Seam audit of one cluster, every verdict from the closed forms of Parts 1 to 5 |
| T53 | Part 6: the whole. Seams of every order: k mechanisms whose every proper subset passes while the whole fails, for signal, assumption and order |
| T54 | Part 6: the whole. Passes an order needs, one plus the most inversions along any path of facts, against simulation on 150 random dependency graphs |
| T55 | Part 6: the whole. The order verdict of the audited cluster under renamings of one configuration |
| T56 | Part 6: the whole. Two webhooks handing facts back and forth, and the shared state counted in informers |
| T78 | Part 1: a shared signal. A scale-up tolerance per direction on the drifting pairing |
| T79 | Part 2: a shared time scale. A capacity buffer sized as a percentage of current replicas |
| T80 | Part 4: a shared assumption. The cold start with the kubelet restart delay reconfigured |
| T81 | Part 6: the whole. Part 1's two fixes on Part 2's nested surge |
| T82 | Part 5: a shared order. A value chain with a member that keeps Never: closed form and enumeration |
| T83 | Part 5: a shared order. Conflicting writers under mixed reinvocation policies |
| T84 | Part 5: a shared order. The patch trail over every order of each scenario |
| T85 | Part 5: a shared order. Expected convergence at the survey's rate of Never |
| T86 | Part 3: a shared state. Prices in seats on a default server |
| T87 | Part 3: a shared state. Partial and rolling triggers |
| T88 | Part 6: the whole. The audited order seam and prevalence under the survey's reinvocation policies |
| T89 | Part 4: a shared assumption. The start-time graph of the surveyed projects at their shipped defaults |
| T90 | Part 1: a shared signal. The paired loops over the tail weight of per-pod usage |
| T91 | Part 1: a shared signal. An autonomic supervisor on the paired loops |
| T92 | Part 1: a shared signal. The transition at the band's edge and the frontier over the tail |
| T93 | Part 2: a shared time scale. Deadlines alone and liveness together |
| T94 | Part 2: a shared time scale. Pareto surge sizes: rounds, time and shortfall |
| T95 | Part 2: a shared time scale. The headroom frontier over the tail |
| T96 | Part 2: a shared time scale. A buffer controller that estimates the tail, and a cap that hides it |
| T97 | Part 3: a shared state. Both safeguards' contracts in a storm |
| T98 | Part 3: a shared state. The boundary and the onset over a tail of list costs |
| T99 | Part 3: a shared state. A controller that splits lists from re-watches |
| T100 | Part 4: a shared assumption. Random start-time graphs and the giant stranded core |
| T101 | Part 4: a shared assumption. A recovery controller, unseen edges and edges that cannot be relaxed |
| T102 | Part 5: a shared order. The passes frontier and an orchestrator that iterates dry-run admission |
| T103 | Parts 1 and 3: hidden memory. Runs that share the visible state and differ in what a mechanism remembers, the backoff's over 200 seeds |
| T104 | Parts 3 and 4: the controllers' frontiers. The split controller's hold, and the relaxation in order |
| T105 | Part 3: a shared state. A storm spreading from the informers a trigger forced |
| T106 | Part 2: a shared time scale. The headroom frontier in slots rather than whole rounds |
| T107 | Part 1: a shared signal. The history statistic: remembered weight sets the first step, and selects where the pair rests inside the band |
| T108 | Part 3: a shared state. The storm onset as a mean-field fold, and a sweep showing no hysteresis below it |
| T109 | Part 6: the whole. The cross-seam frontier of the signal and time-scale seams: drift against surge time for the target, the matched tolerance and the load metric |
| T110 | Part 6: the whole. The storm onset against the list level's share of the server |
| T111 | Part 6: the whole. The order of each seam, the size of its smallest failing set, on the series' systems and on random draws |
| T112 | Part 6: the whole. Each seam's ratio of demand to what its contract gives, and a test cluster at a tenth of the scale |
| T113 | Part 1: a shared signal. The scope of the tail regimes: the noise in the horizontal loop's reading and the share of usage carried by spikes |
| T114 | Part 4: a shared assumption. The heartbeat behind a failing webhook when each failed call takes the webhook timeout |
| T115 | Part 6: the whole. Whole-system tests on incomplete descriptions: which verdicts an omission can move |
| T116 | Part 6: the whole. The assumption x order frontier: four settings of Kyverno and Consul and the pods each leaves outside a webhook |
| T117 | Part 6: the whole. A whole-system supervisor on the signal and time-scale seams at constant demand: greedy by ratio against a coupling-aware choice |
| T118 | Part 1: a shared signal. The split pairing with the heap structure explicit: a live set that follows load, and a heap that grows into its limit |
| T119 | Part 1: a shared signal. The paired loops in transit: a fix applied mid-drift, at three hours |
| T120 | Part 1: a shared signal. The split pairing with a live set that does not follow load: the heap share below which it turns singular, the gain at three heap shares, and each collector's gain over heap shares 0 to 0.95 |
| T121 | Part 2: a shared time scale. The two headroom thresholds: the slots that keep the first rounds free of pending pods, and the fewer that remove the same node waits |
