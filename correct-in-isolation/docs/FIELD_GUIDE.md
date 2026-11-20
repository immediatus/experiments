# Correct in Isolation: Field Guide

This page is for the reader with a cluster and ten minutes. Each seam below gets the symptom it leaves on a dashboard, the test that reads it from what the cluster already holds, and the fixes with their prices. The derivations, the conditions and the numbers behind every line are in the part linked at the head of each section, and the symbols are on [the notation page](NOTATION.md).

## A Shared Signal

From [Two Setpoints for One Number](https://e-mindset.space/blog/correct-in-isolation-part1-two-setpoints-for-one-number/).

**Symptom.** The replica count rises in steps, about every 79.7 hours at the defaults, while requested CPU stays flat and the vertical autoscaler's CPU target falls by the same ratio. That is drift, not growth.

**Test.** List every pair of loops that act on one deployment. If a horizontal and a vertical autoscaler share a metric, compute the step interval $h \log_2(1/(1-p))$ and the step factor $1/((1+m)u_h)$ from their configuration. Then look for steps of that interval and that ratio in the replica history. On a steady load the pair rests only for horizontal targets between 0.791 and 0.966 at the defaults.

**Fixes and their prices.** A target inside the band stops the drift. The pods then run near 87% of their requests, so the headroom the lower target was chosen for is gone. A scale-up tolerance of 0.74 at a 50% target also stops it, and [Every Pair Passes](https://e-mindset.space/blog/correct-in-isolation-part6-every-pair-passes/) prices it in extra rounds when a surge comes. A horizontal metric the vertical loop does not shape, such as requests per second per pod, has a relative gain of one, and the same post shows it repairs both seams. The documented split, horizontal on CPU and vertical on memory, stays safe while the heap stays out of the CPU signal. Check it where a heap grows into its limit.

## A Shared Time Scale

From [Headroom Bought by the Round](https://e-mindset.space/blog/correct-in-isolation-part2-headroom-bought-by-the-round/).

**Symptom.** Desired replicas step up while pods sit unschedulable. Each step pays a full node wait before the next can start.

**Test.** Read the pod autoscaler's desired replica count, whose steps are the rounds, the scheduler's unschedulable queue, and the node autoscaler's nodes by state. Two obvious metrics mislead. The node autoscaler's count of nodes scaled up marks the order, not the capacity, and the kubelet's pod-start latency leaves out image pulls and init containers.

**Fixes and their prices.** Free slots that keep the first $c$ rounds off pending pods remove $c$ node waits for $n_0(g^c - 1)$ slots, fewer for a surge of known size. Removing every wait from a thirtyfold surge, 1,200 seconds down to 360, holds fourteen times the running pods idle. Memory kept as pods, through the pod autoscaler's stabilization window, holds the same node-time as memory kept as nodes and never serves later. When surge sizes have a heavy tail, size the headroom from an estimate of the tail exponent. Never read replica counts the autoscaler's maximum has capped as exact sizes: an exponent of 0.69 then reads as 1.03. Read as censored, they give the right exponent.

## A Shared State

From [A Watch Delayed Becomes a List](https://e-mindset.space/blog/correct-in-isolation-part3-a-watch-delayed-becomes-a-list/).

**Symptom.** Lists and `410 Gone` responses keep coming after an outage has ended, with the server's rejections split between full queues and requests that waited too long.

**Test.** For each watched collection, take the cost of one list, roughly its estimated seats times its execution time. Multiply it by the number of informers that would list it after an outage. For pods that includes every kubelet. Divide by the nominal seat limit of their priority level. The result is the backlog $B$ in seconds. Compare it with the mean watch period plus the history the server keeps. Above that, a storm can hold.

**Fixes and their prices.** A controller that moves lists to a priority level of their own ends storms in the specimen within 54 to 133 minutes. Without a hold it hunts. For an informer on every pod the backlog grows with the square of the cluster, so a test cluster half the size sees a quarter of it.

## A Shared Assumption

From [The Guarantee Nobody Breaks](https://e-mindset.space/blog/correct-in-isolation-part4-the-guarantee-nobody-breaks/).

**Symptom.** Failed calls for pod creation climb in a webhook's own namespace, which is an availability edge binding. Or the webhook steadily refuses its own pods, which is a rejection edge that the next upgrade turns into an outage.

**Test.** Dry-run the creation of a copy of the webhook's own pod. Denied by the webhook means a rejection edge that the first drain binds. Then take each configuration that fails closed and ask whether its rules and selectors match its own pods, another webhook's pods, or an add-on it needs. Each match is a start-time edge, and two webhooks that fail closed and match each other's pods form a cycle. A need for cluster DNS or a network plugin is recorded in no object, so ask the webhook's owners.

**Fixes and their prices.** Excluding the webhook's own namespace and the system namespace, the documented practice, removes its edges to its own pods and to cluster DNS. It removes loops, not cycles: two webhooks that each match the other's pods still need each other. Failing open removes availability edges only: every rejection edge still binds, and requests pass unchecked while the webhook is down. At shipped defaults Kyverno and Consul strand twelve of fifteen components after a full restart, and one exclusion in Consul's selector, or Kyverno failing open, brings every component back.

## A Shared Order

From [The Second Pass Is the Last](https://e-mindset.space/blog/correct-in-isolation-part5-the-second-pass-is-the-last/).

**Symptom.** Some pods are admitted without a sidecar their labels should have brought, or with a signature over an image reference they no longer carry.

**Test.** The audit log records each mutating call with its pass and whether it changed the object. A second pass in which no call mutated anything certifies value links only. A webhook its match rules skipped leaves no trace, so read the match rules too. Submitting the admitted object for admission again, as a dry run, changes it exactly when it is not a common fixed point.

**Fixes and their prices.** The reinvocation setting belongs on the reader. A webhook that reads what others write should opt in, and keeping the default makes its incoming link as fragile as a selector. Names that sort the chain in order repair it at any policy, and any configuration added or renamed later can undo them. Iterating dry-run admission reaches the fixed point in every order, at 43.4 webhook calls against 14.0 at seven webhooks. Two webhooks that write one field to values of their own can fool it.

## The Whole

From [Every Pair Passes](https://e-mindset.space/blog/correct-in-isolation-part6-every-pair-passes/).

**What a review of pairs misses.** A seam has an order, the fewest mechanisms it needs to appear. For a shared signal, a shared assumption and a shared order, seams exist at every order, and a check of pairs sees order two and nothing above.

**Test.** Each seam has a whole-system test that reads what the cluster already holds. For the signal it is the gain matrix, every principal minor positive. For the assumption it is the start-time graph, with no cycle. For the order it is the sorted webhook names and their reinvocation policies, with the passes an order needs at most two. For the state it is the list costs, summed against capacity times the mean watch plus the history. A description that leaves things out can only hide an assumption, order or state failure, so a failing verdict on it stands. The signal's test can err either way, so measure every coupling.

**What to fix first.** The seams that bind at steady state fail every day the cluster runs. On a cluster built from defaults those are the order seam, and the signal seam wherever the two autoscalers share a metric. The seams that need an event fail on the day of the event.
