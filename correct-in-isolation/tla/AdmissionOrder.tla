---------------------------- MODULE AdmissionOrder ----------------------------
(***************************************************************************)
(* Part 5, a shared order.                                                 *)
(*                                                                         *)
(* N mutating webhooks form an enabling chain of value links: webhook 0    *)
(* adds fact 0, and webhook k adds fact k once fact k - 1 is present. Each *)
(* is idempotent and inflationary. The order is any permutation.           *)
(*                                                                         *)
(* Admission runs the contract's passes: a first pass calls every webhook, *)
(* and a second runs only if the first changed the object, calling a       *)
(* webhook again (IfNeeded) only if the object changed after its last      *)
(* call. With Orchestrate, an outside loop repeats admission on the        *)
(* admitted object until no webhook changes it.                            *)
(*                                                                         *)
(* Property: an admission that is done leaves a common fixed point.        *)
(***************************************************************************)
EXTENDS Naturals

CONSTANTS
    N,              \* the webhooks in the chain
    Passes,         \* the passes one admission runs
    Orchestrate,    \* whether an outside loop repeats admission
    MaxAdmissions   \* the most admissions the outside loop runs

Hooks == 0..(N - 1)

\* Every order of the webhooks.
Orders == {f \in [1..N -> Hooks] : \A i, j \in 1..N : i # j => f[i] # f[j]}

\* Webhook h applied to object o, a set of facts.
Apply(h, o) ==
    IF h = 0 THEN o \cup {0}
    ELSE IF (h - 1) \in o THEN o \cup {h}
    ELSE o

\* An object every webhook leaves unchanged.
CommonFixedPoint(o) == \A h \in Hooks : Apply(h, o) = o

VARIABLES
    order,          \* the order the webhooks run in
    obj,            \* the object being admitted
    pos,            \* the position in the order of the next call
    pass,           \* the current pass
    last,           \* last[h]: the object as webhook h last returned it
    changed,        \* whether the current pass changed the object
    admissions,     \* the admissions run so far
    done            \* whether admission has ended

vars == <<order, obj, pos, pass, last, changed, admissions, done>>

Init ==
    /\ order \in Orders
    /\ obj = {}
    /\ pos = 1
    /\ pass = 1
    /\ last = [h \in Hooks |-> {}]
    /\ changed = FALSE
    /\ admissions = 1
    /\ done = FALSE

\* The next webhook in the order, called in the first pass, or in a later pass
\* only if the object changed after its last call.
Call ==
    /\ ~done
    /\ pos <= N
    /\ LET h == order[pos]
           called == pass = 1 \/ last[h] # obj
           new == IF called THEN Apply(h, obj) ELSE obj
       IN  /\ obj' = new
           /\ last' = IF called THEN [last EXCEPT ![h] = new] ELSE last
           /\ changed' = (changed \/ new # obj)
    /\ pos' = pos + 1
    /\ UNCHANGED <<order, pass, admissions, done>>

\* The end of a pass: another pass if one is left and the object changed;
\* otherwise another admission if the outside loop runs and the object is not
\* a common fixed point; otherwise admission is done.
EndPass ==
    /\ ~done
    /\ pos > N
    /\ IF pass < Passes /\ changed
           THEN /\ pass' = pass + 1
                /\ pos' = 1
                /\ changed' = FALSE
                /\ UNCHANGED <<order, obj, last, admissions, done>>
       ELSE IF Orchestrate /\ ~CommonFixedPoint(obj) /\ admissions < MaxAdmissions
           THEN /\ admissions' = admissions + 1
                /\ pass' = 1
                /\ pos' = 1
                /\ changed' = FALSE
                /\ last' = [h \in Hooks |-> {}]
                /\ UNCHANGED <<order, obj, done>>
       ELSE /\ done' = TRUE
            /\ UNCHANGED <<order, obj, pos, pass, last, changed, admissions>>

Next == Call \/ EndPass \/ UNCHANGED vars

Spec == Init /\ [][Next]_vars /\ WF_vars(Call) /\ WF_vars(EndPass)

DoneAtFixedPoint == done => CommonFixedPoint(obj)
WithinN == admissions <= N
Finishes == <>done
===============================================================================
