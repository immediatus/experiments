# Correct in Isolation: Notation

Companion to the six posts listed in [README.md](../README.md). Each post carries the notation it uses; this page gathers all of it in one place.

Every symbol the series uses, grouped by the seam that introduces it. Each part shows only the symbols it uses.

**The tags on each paragraph**

- L1 · Bound, L2 · Fit and L3 · Estimate - the tag on each paragraph: a proof or a cited fact, a judgment or approximation the text argues for, and a worked example computed from the model

**A shared signal**

- $N$ and $r$ - the replica count and the CPU request of one pod
- $D$ and $u = D/(N r)$ - the deployment's CPU demand and its utilization
- $u_h$ and $\text{tol}$ - the horizontal autoscaler's target and its tolerance, 0.1 by default
- $\delta_v$ - the vertical autoscaler's update tolerance: how far a running pod's request may sit from the target before it is updated, at most 0.1
- $u_r$ - the utilization at which the two loops rest: the vertical target $v = 1/((1+m)q)$ on a steady load, and anywhere the update tolerance allows otherwise
- $m$ and $q$ - the vertical autoscaler's margin fraction, 0.15 by default, and the ratio of the usage percentile it sizes from to mean usage
- $h$ and $p$ - the half-life of the vertical autoscaler's usage history, 24 hours by default, and the usage percentile it sizes from, 0.9 by default
- $s^\ast$, $F$ and $T_{\text{dbl}}$ - the interval between the steps of the replica staircase, the factor each step multiplies the replica count by, and the time the count takes to double
- $b$ - the width ratio of the vertical recommender's histogram buckets, 1.05 in its current implementation
- $A_0$, $H_0$ and $r_s$ - the weight the vertical recommender's histogram remembers above the current usage, its whole weight, both in units of one sample at the start, and the samples it takes an hour
- $G$ and $\lambda_{11}$ - a steady-state gain matrix and Bristol's relative gain of its first loop
- $\beta$ and $\theta$ - the elasticity of CPU use with respect to the heap over its live set, which the memory request sets through the limit, and the share of memory use that grows in proportion to per-pod load
- $\theta_L$ and $\xi$ - the share of a runtime's live set that grows in proportion to per-pod load, and the elasticity of observed memory with respect to the memory request
- $s_H$ - the heap's share of the memory the vertical loop observes
- $\gamma$ - the elasticity of a pod's service rate with respect to its CPU request, on a custom metric
- $\sigma$ and $z_p$ - the shape of a lognormal factor on per-pod usage, and the standard normal quantile of the percentile $p$
- $\Phi$ - a composite's history statistic: the least function of its past that, added to the observed state, makes it Markov again

**A shared time scale**

- $g = \ell/(r\,u_h)$ - the growth factor: the most the pod autoscaler can multiply its ready pods by in one round when its metric is saturated, $\ell$ the CPU limit
- $k$ and $R$ - the size of a surge as a multiple of the load before it, and the rounds a saturated metric needs to meet it
- $\tau_{\text{pod}}$ and $\tau_{\text{node}}$ - the dead times of a pod and of a node, from the order to capacity that serves
- $n_0$, $H$ and $c$ - the running pods before a surge, the free pod slots held in advance, and the rounds those slots cover
- $T_2$ and $C = R(\tau_{\text{pod}} + \tau_{\text{node}})$ - the time until capacity meets a second surge, and the time a surge takes with no capacity held
- $S$, $U$ and $M = S + U$ - the pod autoscaler's downscale stabilization window, the node autoscaler's unneeded time, and the memory they keep together after a surge
- $T_g$, $\mu$ and $N_s$ - the gap between the end of one surge and the start of the next, its mean, and the spare nodes a surge leaves
- $W$, $\nu$ and $J = W + \nu\,T_2$ - the node-time held in the gap, the exchange rate in node-seconds per second short of capacity, and the cost
- $U_{\text{be}}$ and $S_{\text{be}}$ - the break-even unneeded time and the break-even window
- $\bar{F}$, $f$ and $\zeta = f/\bar{F}$ - the survival function, density and hazard of the gap
- $\Delta$ - a deadline: the time within which a loop promises capacity after a surge
- $a$ and $k_{\min}$ - the tail exponent of surge sizes, a surge exceeding $k$ with probability $(k_{\min}/k)^a$, and the smallest surge the tail describes
- $N^\ast$ - the pods a surge needs for their limits to cover it
- $k_{\max}$ - the largest surge a capped replica count can show: the replica maximum read as a surge size
- $V$ and $\phi$ - the pod-seconds of demand served short while capacity meets a surge, and the slot-seconds a team would pay to serve one of them

**A shared state**

- $N_I$ - the informers, each holding one watch
- $\omega$ and $\omega_0$ - the server work of one list and of one re-watch, in seat-seconds
- $\kappa$ and $B = N_I\,\omega/\kappa$ - the server's capacity in seat-seconds of work per second, and the backlog a trigger forcing every informer to list builds
- $T_h$ - the retained history: how long after a change a watch can still resume from it
- $T_{\min}$ and $\bar{T}$ - the shortest and the mean watch period
- $T_q$ and $T_b$ - the server's queue wait limit and the cap on the client's backoff
- $p_r$, $\varphi$, $b_i$ and $E$ - in a saturated storm, the probability an attempt is rejected, the share of cycles that end in a list, the backoff after the $i$-th rejection, and the time a turned-away client spends trying

**A shared assumption**

- $Q$, $K$ and $Z$ - the nodes of a cluster, the nodes that fail, and the distinct nodes the replicas of a start-time cycle occupy
- $n_w$ and $a_w$ - a webhook's replicas, and the minimum its disruption budget keeps available
- $n_a$ and $\tau_f$ - the replicas of an application the webhook checks, and a node's mean time between failures

**A shared order**

- $x$ and $w_i(x)$ - the object being admitted, and mutating webhook $i$ as a function of it
- $n_c$ and $d = n_c - 1$ - the webhooks in an enabling chain, and its depth
- $P$ - the passes an admission runs over its mutating webhooks, two under the reinvocation contract
- $A(n_c, j)$ - the Eulerian number: the orders of $n_c$ items with exactly $j$ descents
- $\eta$ - the position in a chain of the member that its last match link leads into, counting the first member as zero

**The whole**

- $n$ and $t$ - the mechanisms in a set, and the size of the subsets a check covers: a $t$-wise check tests every subset of at most $t$
- $\alpha$ - the coupling between every two of $n$ symmetric loops
- $\rho(f)$ - for a fact $f$ a webhook writes, the most inversions along any path of the facts it needs, in a given order
- $\text{anc}(f)$ - the fact $f$ with every fact it needs, directly or through others
- $\Pi$ and $\mathcal{N}$ - a seam's ratio of what the composite asks to what the contracts give, and the matrix of a start-time graph's needs
