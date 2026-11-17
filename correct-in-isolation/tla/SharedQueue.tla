----------------------------- MODULE SharedQueue ------------------------------
(***************************************************************************)
(* Part 3, a shared state, and the bounded network the formal side         *)
(* assumes.                                                                *)
(*                                                                         *)
(* K informers each watch for W ticks, then resume with a re-watch (one    *)
(* tick of server work). A re-watch served more than H ticks after its     *)
(* watch ended is answered 410, and the informer lists (L ticks of work).  *)
(* The server works one tick at a time through one first-in-first-out     *)
(* queue or, with InstantServe, serves every request on arrival. A network *)
(* partition can cut an informer's watch for up to MaxCut ticks; it        *)
(* resumes when the partition ends. A trigger at the start forces every    *)
(* informer to list.                                                       *)
(*                                                                         *)
(* Contracts: the overload protection serves in order; the re-list rule    *)
(* answers expired versions with 410 and lists. The composite property:    *)
(* the lists eventually stop, <>[]Calm.                                    *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    K,              \* the informers
    W,              \* the ticks a watch lasts
    H,              \* the retained history, ticks
    L,              \* the server work of a list, ticks
    InstantServe,   \* whether the server serves every request on arrival
    MaxCut          \* the longest partition, ticks; 0 for none

Informers == 1..K

VARIABLES
    phase,          \* phase[i]: "watch", "cut", "rewatch" or "list"
    w,              \* w[i]: the ticks left in informer i's watch
    age,            \* age[i]: the ticks since informer i's watch ended
    cut,            \* cut[i]: the ticks left in informer i's partition
    queue,          \* the server's queue of <<informer, kind>> requests
    work,           \* the ticks of work done on the request at the head
    gone            \* whether any re-watch has been answered 410

vars == <<phase, w, age, cut, queue, work, gone>>

\* The server work of a request.
Cost(kind) == IF kind = "list" THEN L ELSE 1

\* The trigger: every informer lists, queued in informer order.
Init ==
    /\ phase = [i \in Informers |-> "list"]
    /\ w = [i \in Informers |-> 0]
    /\ age = [i \in Informers |-> 0]
    /\ cut = [i \in Informers |-> 0]
    /\ queue = [i \in Informers |-> <<i, "list">>]
    /\ work = 0
    /\ gone = FALSE

\* A partition cuts a watching informer off for d ticks.
Cut(i) ==
    /\ MaxCut > 0
    /\ phase[i] = "watch"
    /\ cut[i] = 0
    /\ \E d \in 1..MaxCut : cut' = [cut EXCEPT ![i] = d]
    /\ phase' = [phase EXCEPT ![i] = "cut"]
    /\ age' = [age EXCEPT ![i] = 0]
    /\ UNCHANGED <<w, queue, work, gone>>

\* The outcome for informer i of serving its request of the given kind: a list
\* starts a watch; a re-watch past the history is answered 410 and lists.
Served(i, kind, ph, ww, ag) ==
    IF kind = "list" THEN [ph |-> "watch", ww |-> W, ag |-> 0, lst |-> FALSE]
    ELSE IF ag > H THEN [ph |-> "list", ww |-> 0, ag |-> 0, lst |-> TRUE]
    ELSE [ph |-> "watch", ww |-> W, ag |-> 0, lst |-> FALSE]

\* One tick: watches run down, waiting re-watches and cuts age, the server works.
Tick ==
    LET \* the informers whose watch ends, or whose partition heals, this tick
        ended == {i \in Informers : phase[i] = "watch" /\ w[i] = 1}
        healed == {i \in Informers : phase[i] = "cut" /\ cut[i] = 1}
        arrivals == ended \cup healed
        \* the informers' state after the tick, before the server acts
        ph1 == [i \in Informers |-> IF i \in arrivals THEN "rewatch" ELSE phase[i]]
        w1 == [i \in Informers |-> IF phase[i] = "watch" /\ w[i] > 1 THEN w[i] - 1 ELSE w[i]]
        ag1 == [i \in Informers |->
                   IF i \in ended THEN 0
                   ELSE IF phase[i] \in {"rewatch", "cut"} \/ i \in healed
                       THEN IF age[i] > H THEN H + 1 ELSE age[i] + 1
                   ELSE age[i]]
        cut1 == [i \in Informers |-> IF cut[i] > 0 THEN cut[i] - 1 ELSE 0]
        \* the arrivals' re-watches, queued in informer order
        newreq == [j \in 1..Cardinality(arrivals) |->
                      <<CHOOSE i \in arrivals : Cardinality({x \in arrivals : x < i}) = j - 1,
                        "rewatch">>]
        q1 == queue \o newreq
    IN  IF InstantServe
        THEN \* every waiting request is served at once; a 410 adds a list, also
             \* served at once
             LET out == [i \in Informers |->
                            IF ph1[i] = "rewatch"
                                THEN Served(i, "rewatch", ph1[i], w1[i], ag1[i])
                            ELSE IF ph1[i] = "list"
                                THEN Served(i, "list", ph1[i], w1[i], ag1[i])
                            ELSE [ph |-> ph1[i], ww |-> w1[i], ag |-> ag1[i], lst |-> FALSE]]
             IN  /\ phase' = [i \in Informers |-> IF out[i].lst THEN "watch" ELSE out[i].ph]
                 /\ w' = [i \in Informers |-> IF out[i].lst THEN W ELSE out[i].ww]
                 /\ age' = [i \in Informers |-> out[i].ag]
                 /\ gone' = (gone \/ \E i \in Informers : out[i].lst)
                 /\ cut' = cut1
                 /\ queue' = <<>>
                 /\ work' = 0
        ELSE IF q1 = <<>>
        THEN \* nothing to serve
             /\ phase' = ph1
             /\ w' = w1
             /\ age' = ag1
             /\ cut' = cut1
             /\ queue' = q1
             /\ work' = 0
             /\ UNCHANGED gone
        ELSE \* the server works one tick on the request at the head of the queue
             LET head == Head(q1)
                 done == work + 1 >= Cost(head[2])
                 out == Served(head[1], head[2], ph1[head[1]], w1[head[1]], ag1[head[1]])
             IN  IF done
                 THEN /\ phase' = [ph1 EXCEPT ![head[1]] = out.ph]
                      /\ w' = [w1 EXCEPT ![head[1]] = out.ww]
                      /\ age' = [ag1 EXCEPT ![head[1]] = out.ag]
                      /\ queue' = IF out.lst
                                      THEN Tail(q1) \o <<<<head[1], "list">>>>
                                      ELSE Tail(q1)
                      /\ gone' = (gone \/ out.lst)
                      /\ work' = 0
                      /\ cut' = cut1
                 ELSE /\ phase' = ph1
                      /\ w' = w1
                      /\ age' = ag1
                      /\ cut' = cut1
                      /\ queue' = q1
                      /\ work' = work + 1
                      /\ UNCHANGED gone

Next == Tick \/ \E i \in Informers : Cut(i)

Spec == Init /\ [][Next]_vars /\ WF_vars(Tick)

\* No informer is listing.
Calm == \A i \in Informers : phase[i] # "list"

EventuallyCalm == <>[]Calm
NoGone == ~gone
===============================================================================
