# Falsification Criteria

Each force the series names comes with observations that would refute it, one on people and one on agents,
each with the condition, the prediction and what would count as a refutation. They are predictions: the
posts were written without running them, and nothing here claims they have been confirmed. Anyone with
review records or an agent panel can test them and report the outcome, refutations included, as
[Reporting a run](#reporting-a-run) describes.

## Status

| Criterion | Part | What it tests | Predictions from | Status |
|---|---|---|---|---|
| F1 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | Correlated experience sets a floor | T1, T2 | predicted, not yet run |
| F2 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | Sequential votes lock in | T3, T8 | predicted, not yet run |
| F3 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | The endorsed senior stays silent | T4 | predicted, not yet run |
| F4 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | The veto cliff | T5, T9 | predicted, not yet run |
| F5 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | Reversibility narrows the band | T6, T9 | predicted, not yet run |
| F6 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | Stated reasons mislead the record | T7 | predicted, not yet run |
| F7 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | Groups that decide apart stall the review | T26 | predicted, not yet run |
| F8 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | The window closes on conversations | T27 | predicted, not yet run |
| F9 | [1](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | Simple pieces stall the review | T27 | predicted, not yet run |
| F10 | [2](https://e-mindset.space/blog/adoption-mechanics-part2-smarter-agents-fewer-opinions/) | Stronger models, fewer opinions | T12, T13, T19 | predicted, not yet run |
| F11 | [2](https://e-mindset.space/blog/adoption-mechanics-part2-smarter-agents-fewer-opinions/) | The upgrade condition | T11, T12 | predicted, not yet run |
| F12 | [2](https://e-mindset.space/blog/adoption-mechanics-part2-smarter-agents-fewer-opinions/) | Correlation erases the cost of herding | T14 | predicted, not yet run |
| F13 | [2](https://e-mindset.space/blog/adoption-mechanics-part2-smarter-agents-fewer-opinions/) | The informed minority, diluted | T15, T17 | predicted, not yet run |

## The criteria

**F1. Correlated experience sets a floor.** People: in a body of past review decisions with known outcomes,
estimate each reviewer's error and the latent correlation of their errors; the majority's error of panels of
growing size levels off near Proposition 1's floor instead of falling toward zero. Agents: the same with
models of one provider answering a held-out benchmark. Refuted if the majority error of large panels falls
below the floor by more than its sampling error. Ground truth and null: outcomes observed after deployment, such as incident and rollback records or canary telemetry, or a pre-registered held-out set of decisions; the null is independent errors, under which a majority's error keeps falling as the panel grows.

**F2. Sequential votes lock in.** People: the same proposals decided by a sequential open vote and by a
blind simultaneous poll; the sequential vote adopts proposals later judged worse more often, and a silent
champion costs more under it. Agents: agents answering in turn with earlier answers in context, against the
same agents answering independently. Refuted if the sequential condition adopts worse proposals no more often
than the blind one, or a silent champion costs the same under both. Ground truth and null: each proposal's quality judged afterwards from canary or deployment telemetry, or by blind re-rating; the null is no difference between the two conditions.

**F3. The endorsed senior stays silent.** People: offered an anonymous channel, dissent rises most among
senior reviewers who endorsed the incumbent, and least among those who did not. Agents: an agent whose
context records its own earlier endorsement of the incumbent dissents less than one without that record.
Refuted if the endorsed group's dissent does not rise more under anonymity, or the record does not lower
the agent's dissent. Ground truth and null: dissent counted in the review record; the null is anonymity raising dissent equally across seniority and past endorsement.

**F4. The veto cliff.** People: in an organization whose current design satisfies each gate better than any
single change could satisfy all of them, no proposal passes in a review period, whatever its measured merit.
Agents: veto-holding agents given ideal points around the status quo reject every candidate. Refuted if a
proposal passes every gate while the status quo lies inside the hull of their stated priorities. Ground truth and null: the gates' priorities written down before the review; the null is a pass rate that does not depend on where the status quo sits among them.

**F5. Reversibility narrows the band.** People: the same proposal offered as a permanent change and as a
reversible pilot; the pilot is adopted at a smaller measured advantage. Agents: an agent deciding under a
stated switching cost adopts at a lower advantage when the cost is reduced. Refuted if lowering the
switching cost does not lower the advantage needed to adopt. Ground truth and null: the advantage measured in pilot or canary telemetry; the null is the same adoption threshold for the pilot and the permanent change.

**F6. Stated reasons mislead the record.** People: reasons recorded in postmortems compared with what
telemetry shows drove the outcome; when the recorded reasons agree with the drivers less often than the bias's
size over the gap between driver and bias (four times in nine in the running case), a model fitted to the reasons points the wrong way, and no statistic of the reasons alone
flags it. Agents: the same with an agent's stated rationale against measured feature attributions. Refuted if
a model fitted to unfaithful reasons recovers the driver's sign, or a test on the reasons alone detects the
bias. Ground truth and null: the driver measured from telemetry that does not pass through the recorded reasons; the null is a reasons-based estimate that matches it.

**F7. Groups that decide apart stall the review.** People: comparable proposals reviewed by groups that meet
apart and exchange their conclusions, and by the same people meeting together; the groups meeting apart stop
more proposals in the review, those later judged better as well as worse. Agents: sub-panels of agents that
each reach a verdict before seeing the others' verdicts, against one panel. Refuted if groups meeting apart stop
proposals later judged better no more often than the joint meeting does. Ground truth and null: the quality of stopped proposals judged from shadow pilots or later reimplementation; the null is the same stop rate under both arrangements.

**F8. The window closes on conversations.** People: decisions that need sign-off from a varying number of
groups before a fixed deadline; the share decided in time falls slowly at first and then sharply as the groups
grow, faster than in proportion to their number. Agents: orchestrations that must reconcile a growing number of
agents' conclusions within a fixed budget of turns. Refuted if the share decided in time falls no faster than
in proportion to the number of groups, or does not fall at all. Ground truth and null: decision timestamps against the deadline; the null is a time to decide that does not depend on the number of groups.

**F9. Simple pieces stall the review.** People: comparable designs reviewed whole and reviewed as separate
pieces; each piece draws more participants with an opinion than the whole design did, and the split review
concludes less often. Refuted if splitting a design does not raise participation per piece, or the split review
concludes as often as the whole one. Ground truth and null: review records of participants, comments and completion; the null is participation per piece equal to the whole design's.

**F10. Stronger models, fewer opinions.** Agents: on a new benchmark with per-question results, the pooled
odds of a shared mistake rise with the pair's accuracy, an average of the strongest models' votes holds fewer
than 2.5 independent opinions, and within strata of similar difficulty the odds ratio sits near 1 except among
the strongest pairs, where it stays above 1. People: in a profession with shared training, experts' errors
concentrate on the same hard cases. Refuted if the pooled dependence falls with capability on new data, or the
residual among the strongest pairs vanishes on a benchmark where the middle of the range shows none. Ground truth and null: the answer keys of a held-out benchmark, or the verified outcomes of real decisions; the null is the item-response model with one difficulty per question, under which models share nothing but difficulty.

**F11. The upgrade condition.** Agents: for any upgrade of every panel member whose measured p and rho give a
negative margin, the measured majority error of a large panel rises; near the top of the accuracy range,
smaller rises in correlation suffice (Corollary 1). People: a team hired from one background after a mixed
one, with p and rho measured before and after. Refuted if the panel improves on a path with a negative margin,
or worsens on one with a positive margin, beyond sampling error. Ground truth and null: a held-out evaluation set scored before and after the upgrade; the null is the floor computed as if the members' errors were independent.

**F12. Correlation erases the cost of herding.** People and agents: the same members deciding in sequence and
in a blind vote, with independent and with correlated signals. Prediction: the sequence's excess error over
the blind vote shrinks as signals correlate, from 14 points with independent signals to nothing at a
correlation of 0.75 in the model, under any rule from myopic to strongly probing. Refuted if the excess error
is as large under correlated signals as under independent ones. Ground truth and null: the answer keys of the questions; the null is the same agents answering blind.

**F13. The informed minority, diluted.** Mixed panels of agents and people of whom some hold a local fact,
run on questions where the fact favours the successor and where it opposes it, with the agents' sensitivity
to the fact measured on past questions. Prediction: agents whose answers do not move with the fact dilute the
people's information under every unweighted rule tried, the surprisingly-popular rule included; agents
whose answers move with it by enough improve on the people alone, and more dependent agents need to move more.
Refuted if blind-spotted agents improve on the people alone, or informative agents fail to once they move with
the fact by more than the predicted amount. Ground truth and null: the local fact verified after the decision; the null is the people's own majority.

## Reporting a run

Open an issue with the criterion number, the setting, and the observation. A report attaches:

- for people: the number of decisions, how outcomes were judged, how the decision order or anonymity was
  set, and the counts behind every rate;
- for agents: the models and their versions, the prompts, the decoding settings, the number of questions,
  and per-question results or their pairwise counts;
- the section of `reproduce.py` whose prediction the run is compared with, and the inputs changed to match
  the setting, so that the prediction can be recomputed.

A run that cannot meet a criterion's condition is reported as such and leaves the status unchanged.
