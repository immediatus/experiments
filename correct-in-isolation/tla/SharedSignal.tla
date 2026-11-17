----------------------------- MODULE SharedSignal -----------------------------
(***************************************************************************)
(* Part 1, a shared signal.                                                *)
(*                                                                         *)
(* A horizontal autoscaler sets the replica count n so that utilization    *)
(* D / (n r) sits within Tol percent of its target T percent. A vertical   *)
(* autoscaler sets the per-pod request r to (100 + M) percent of per-pod   *)
(* usage D / n, the steady-load setpoint of the recommender (q = 1).       *)
(* Integer units: D and r in millicores.                                   *)
(*                                                                         *)
(* Each loop's contract is the liveness property that it eventually rests, *)
(* <>[] Rest. Checked alone, with the other loop frozen, it holds; checked *)
(* together it holds only when the target lies inside the band both loops  *)
(* allow.                                                                  *)
(***************************************************************************)
EXTENDS Integers

CONSTANTS
    D,              \* the deployment's CPU demand, millicores
    T,              \* the horizontal target, percent
    Tol,            \* the horizontal tolerance, percent
    M,              \* the vertical margin, percent
    NInitMax,       \* replica counts 1..NInitMax are starting points
    RInit,          \* requests that are starting points, millicores
    Nmax,           \* the horizontal autoscaler's replica ceiling
    HorizontalOn,   \* whether the horizontal loop acts
    VerticalOn      \* whether the vertical loop acts

VARIABLES
    n,              \* the replica count
    r               \* the request of one pod, millicores

vars == <<n, r>>

CeilDiv(a, b) == (a + b - 1) \div b
Abs(x) == IF x < 0 THEN -x ELSE x
Min(a, b) == IF a < b THEN a ELSE b

\* The horizontal loop rests: |D / (n r T/100) - 1| <= Tol/100, in integers.
RestH == Abs(100 * D - n * r * T) * 100 <= Tol * n * r * T

\* The replica count the horizontal rule asks for, capped at the ceiling.
DesiredN == Min(CeilDiv(100 * D, r * T), Nmax)

\* The vertical loop's target request, and its rest at that request.
RStar == CeilDiv((100 + M) * D, 100 * n)
RestV == r = RStar

\* Every starting point in the given ranges: TLC checks the properties from each.
Init ==
    /\ n \in 1..NInitMax
    /\ r \in RInit

Horizontal ==
    /\ HorizontalOn
    /\ ~RestH
    /\ DesiredN # n
    /\ n' = DesiredN
    /\ UNCHANGED r

Vertical ==
    /\ VerticalOn
    /\ ~RestV
    /\ r' = RStar
    /\ UNCHANGED n

Next == Horizontal \/ Vertical \/ UNCHANGED vars

Spec == Init /\ [][Next]_vars /\ WF_vars(Horizontal) /\ WF_vars(Vertical)

TypeOK == n \in 1..Nmax /\ r \in Nat

HorizontalSettles == <>[] RestH
VerticalSettles == <>[] RestV
PairSettles == <>[] (RestH /\ RestV)
===============================================================================
