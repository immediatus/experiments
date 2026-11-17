------------------------------ MODULE StartCycle ------------------------------
(***************************************************************************)
(* Part 4, a shared assumption.                                            *)
(*                                                                         *)
(* Each component guarantees to start once every component it needs is    *)
(* up: (\A d \in Needs[c] : up[d]) ~> up[c]. After a full restart every    *)
(* component is down. TLC checks each guarantee, and the composite         *)
(* liveness that every component eventually runs. Abadi and Lamport's      *)
(* second example is the case Needs = a -> b, b -> a.                     *)
(***************************************************************************)
EXTENDS Naturals

CONSTANTS
    Comps,          \* the components
    Needs           \* Needs[c]: the components c needs in order to start

VARIABLES
    up              \* up[c]: whether component c is running

vars == <<up>>

\* A full restart: every component is down.
Init == up = [c \in Comps |-> FALSE]

\* A component starts once everything it needs is up.
Start(c) ==
    /\ ~up[c]
    /\ \A d \in Needs[c] : up[d]
    /\ up' = [up EXCEPT ![c] = TRUE]

Next == \E c \in Comps : Start(c)

Spec == Init /\ [][Next]_vars /\ \A c \in Comps : WF_vars(Start(c))

\* The documented mutual case: webhook a matches the pods of b, which matches
\* the pods of a, with an application behind a.
CycleNeeds ==
    [c \in {"a", "b", "app", "dns"} |->
        CASE c = "a"   -> {"b"}
          [] c = "b"   -> {"a"}
          [] c = "app" -> {"a"}
          [] c = "dns" -> {}]

\* The same set with the cycle cut: a needs DNS instead of b.
AcyclicNeeds ==
    [c \in {"a", "b", "app", "dns"} |->
        CASE c = "a"   -> {"dns"}
          [] c = "b"   -> {"a"}
          [] c = "app" -> {"a"}
          [] c = "dns" -> {}]

\* Each component's own guarantee, and the composite liveness.
Guarantee(c) == (\A d \in Needs[c] : up[d]) ~> up[c]
EveryGuarantee == \A c \in Comps : Guarantee(c)
AllUp == <>(\A c \in Comps : up[c])
===============================================================================
