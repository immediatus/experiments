------------------------------ MODULE NestedPair ------------------------------
(***************************************************************************)
(* Part 2, a shared time scale.                                            *)
(*                                                                         *)
(* A pod loop doubles its ready pods each round (a saturated metric,       *)
(* growth factor 2), counting pods not yet ready at zero, so it asks for a *)
(* round only when the last round's pods are ready. Pods start in free     *)
(* slots and are ready TauP ticks later; pods without a slot wait for the  *)
(* node loop, which adds slots TauN ticks after it sees them pending. A    *)
(* tick is 30 seconds, and every surge size in Needs is checked.           *)
(*                                                                         *)
(* Each loop's contract is a deadline: capacity meets the surge within a   *)
(* number of ticks set by the rounds R it needs. TLC checks each deadline  *)
(* as an invariant over a clock, and liveness as <>Met. With Separated the *)
(* node loop provisions for the final need at the first pending pod, the   *)
(* counterfactual of a node loop that could see it.                        *)
(***************************************************************************)
EXTENDS Naturals

CONSTANTS
    N0,             \* the running pods before the surge
    Needs,          \* the surge sizes checked, as the pods each needs
    TauP,           \* a pod's dead time, ticks
    TauN,           \* a node's dead time, ticks
    Slots0,         \* free pod slots held before the surge
    Separated,      \* whether the node loop provisions for the final need
    Horizon         \* the ticks the clock runs

VARIABLES
    need,           \* the pods this surge needs
    t,              \* the clock, ticks
    ready,          \* the pods ready
    batch,          \* the pods of the current round
    stage,          \* "idle", "node" (waiting for nodes) or "pod" (starting)
    timer,          \* the ticks left in the current stage
    slots           \* the free pod slots

vars == <<need, t, ready, batch, stage, timer, slots>>

Min(a, b) == IF a < b THEN a ELSE b

Init ==
    /\ need \in Needs
    /\ t = 0
    /\ ready = N0
    /\ batch = 0
    /\ stage = "idle"
    /\ timer = 0
    /\ slots = Slots0

\* The pod loop asks for the next round; the scheduler places what fits; the
\* node loop is told about the rest at once.
Ask ==
    /\ stage = "idle"
    /\ ready < need
    /\ batch' = Min(2 * ready, need) - ready
    /\ IF slots >= Min(2 * ready, need) - ready
           THEN /\ stage' = "pod"
                /\ timer' = TauP
                /\ slots' = slots - (Min(2 * ready, need) - ready)
           ELSE /\ stage' = "node"
                /\ timer' = TauN
                /\ slots' = IF Separated THEN need - ready - batch' ELSE 0
    /\ UNCHANGED <<need, t, ready>>

\* One tick of the clock: a node wait or a pod start runs down.
Tick ==
    /\ t < Horizon
    /\ stage # "idle"
    /\ t' = t + 1
    /\ IF timer > 1
           THEN /\ timer' = timer - 1
                /\ UNCHANGED <<need, stage, ready, batch, slots>>
           ELSE IF stage = "node"
                    THEN /\ stage' = "pod"
                         /\ timer' = TauP
                         /\ UNCHANGED <<need, ready, batch, slots>>
                    ELSE /\ stage' = "idle"
                         /\ timer' = 0
                         /\ ready' = ready + batch
                         /\ batch' = 0
                         /\ UNCHANGED <<need, slots>>

Next == Ask \/ Tick \/ UNCHANGED vars

Spec == Init /\ [][Next]_vars /\ WF_vars(Ask) /\ WF_vars(Tick)

\* Capacity meets the surge.
Met == ready >= need

\* The rounds a saturated metric needs: the least R with N0 * 2^R >= need.
Rounds == CHOOSE k \in 0..20 : N0 * 2^k >= need /\ (k = 0 \/ N0 * 2^(k - 1) < need)

\* The three deadlines: the pod loop alone, a node loop that saw the final
\* need, and the nested pair.
PodDeadline == t > Rounds * TauP => Met
SeparatedDeadline == t > Rounds * TauP + TauN => Met
NestedDeadline == t > Rounds * (TauP + TauN) => Met

Live == <>Met
===============================================================================
