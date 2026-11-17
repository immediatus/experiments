# P models of the seams' hidden memory

TLC (`../tla/`) checks each seam's contracts as predicates on the visible state. The models here check
the state the predicates leave out: a client's backoff, a reconciler's timer against a ReplicaSet's
retry, and the calls a first admission pass made. They are written in P, the language of communicating
state machines of Desai and five coauthors (PLDI 2013, doi:10.1145/2491956.2462184), and checked with
`p check`, which explores schedules and choices at random from a fixed seed. A verdict that no schedule
broke a property is a finding over the schedules explored, not a proof.

Run: `python3 run.py [--check]` (needs the .NET 8 SDK and `dotnet tool install P`; P 3.1.0 was used).

## What each model keeps and what it abstracts

**SharedBackoff (Part 3).** Kept: the Reflector's documented backoff, 0.8 s doubling to a cap of 30 s,
jittered to one or two times its base, reset when more than two minutes have passed since the last reset;
the queue's 15 s wait limit; the 300 s history; the client's starting state, fresh or raised, which is the
seam's history statistic. Abstracted: the queue is replaced by a choice of how many times in a row it turns
the client away, 0 to 20. That over-approximates every queue, so a property that holds for every choice
holds for any server; long runs are explored as often as short ones. The jitter is explored at its two
extremes and the served attempt's wait at 0 and the full limit. Waiting longer only brings a 410 nearer, so
the wait's extremes are the worst cases; for the jitter, a search over a grid of 41 values from 1 to 2
gives the same fewest runs as the extremes, 11 fresh and 8 raised. One client is modeled, because the
property is about one client's run.

**RepairRace (Part 4).** Kept: a webhook with one replica whose configuration fails closed and matches its
own pods; admission of a pod once, at creation, when the configuration is absent or a webhook pod is ready;
readiness 90 s after admission; a reconciler that re-applies the configuration 5 s after it is deleted
unless paused; a ReplicaSet that creates the pod at its next retry and doubles the retry after it, or at
once when nudged. A clock that advances only when every machine has acknowledged a second keeps the
machines' times aligned, and within a second the order of their requests is left to the checker.
Abstracted: the ReplicaSet's next retry after an outage is chosen from 1, 2, 4 ... 512 s, a sample of where
its doubling backoff can stand; nodes, scheduling and image pulls are folded into the 90 s.

**AdmissionPasses (Part 5).** Kept: a label webhook and an injector selected by that label, both opted in;
a first pass over every webhook whose selector matches the object as it stands at its turn; a second pass
that calls a webhook only if the first called it and the object changed after its call; both orders.
Abstracted: the pod is two facts, the label and the sidecar; the dispatcher calls webhooks synchronously,
which the API server does.

## Checks and their frozen verdicts

`expected.txt` holds one line per check. The tight backoff checks ask for one rejection more than the bound,
so the checker must find a 410 at exactly the bound: it is reached, not only respected.
