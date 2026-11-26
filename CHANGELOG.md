# Changelog

Releases are tagged `<series-slug>-v<major>.<minor>`. A published experiment changes only by a
dated erratum recorded here, with what changed, why, and which numbers moved.

## Unreleased

### Repository

- Shared checks: `tools/check_all.py` runs every check of every experiment, locally and in continuous
  integration, with each reproduction under two hash seeds; `tools/lint.py` runs ruff with the pinned rules
  (pycodestyle, pyflakes, sorted imports, imports at module top, no import of another module's private name,
  explicit file encodings) and a standard-library fallback; `tools/coverage.py` measures model coverage;
  `tools/check_docs.py` checks every document against the code and the results.
- CONVENTIONS.md sets the standard every experiment follows: one function per closed form and per simulated
  mechanism, constants called from the function that computes them, `math.fsum` for floating-point sums, and a
  part page per post that restates its belief, mechanism, law, results, bill and reversal condition.
- A development container (`.devcontainer/`) with every tool the checks use, so TLC and P run instead of being
  skipped; TLA+, P and .NET build output kept out of version control.

### adoption-mechanics

- The experiment behind *Adoption Mechanics* (three parts): one member model for people and agents, with
  sensors, aggregation, hand-off and actuator composed for a running case of 15 reviewers, 3 layers and 4
  approvers (architecture board, engineering manager, security, product); every lever priced on better and worse
  designs, and the achievable region of all 64 combinations; the write-back loop with its non-identification.
  The review can be held by groups that hold unequal evidence and decide apart, and the life of a design records
  where each review ends, including the deaths that cross-communication causes without anyone saying no (the
  decision window, conclusions carried between groups, vetoes multiplying, and the law of triviality, under which
  a design split into simple pieces stalls); the actuator includes the agenda setter, whose one compromise lands
  the status quo in the approvers' hull and ends change. AI enters the same review as an instrument: a model's
  recall of a fact by its position in a long document, calibrated on the published accuracy-by-position of six
  models, read whole or in overlapping parts; an agreement mediator that carries conclusions between groups against
  a difference mediator that pools blind judgments by reliability, in every speaking order; a debate heard before or
  after the vote, single advocates, and critics whose false flags people verify in part, under the condition by which
  a shared input captures the panel; the region of all 81 combinations of instruments; and instruments that share a source, where roles of one model
  prompted differently err together at the floor of that source however many there are, while a check grounded
  in the running system (tests, telemetry, static analysis) is a source of its own; the majority error of a
  correlated panel is computed exactly as well as simulated. In mixed panels, Proposition 6 gives the large-panel law of
  common-mode dilution: agents sharing a blind spot set the chance of adopting a worse design whatever the people know.
  A shared input is weighed against each member's own signal, group by group, so an input can capture some groups of
  a review and not others. The human energy budget runs through the series: a review's settlements form a mesh,
  quadratic in the opinion holders, and the residual protocol reconciles against the machines' reference instead, a
  star, linear in them (Proposition 8), computed exactly beside Part 1's law of triviality. Part 3's framework,
  the Residual Protocol, is computed in its parts: past Part 1's levers only accuracy and the independence of errors
  move a review, and a shared briefing buys less than evidence of one's own; routing to the holders of each fact; a
  machine list blind to the flaw against the questions holders add; and the nearest version of a design every
  approver prefers. 43 sections, 194 unit
  tests, 9 figures, all built from the frozen results (the attention figure is a table drawn in the post), 23 falsification criteria (four testing the Residual Protocol, the framework the series proposes) and a companion page per part.
- Measured: pairwise right/wrong counts, overall and within 5 and 10 strata of question difficulty, for Stanford
  HELM Lite MMLU (95 models) and HELM Capabilities GPQA (65) and MMLU-Pro (64); counts only, licence unstated.
  Pooled dependence of errors rises with capability on all three; within difficulty it sits at an
  item-response null except among the strongest pairs, which exceed it; no measured upgrade meets the
  condition under which a better panel becomes a worse one.
- Calibrated: reviewer precision and within-review error correlation against peer review (journal reliability
  meta-analysis; NeurIPS 2014 and 2021 consistency experiments; panel and field experiments), with the running
  case rerun at calibrated constants, with asymmetric precision and negativity-biased herding, and with part of
  the shared error local to each partitioned group.

### correct-in-isolation

- The experiment behind *Correct in Isolation* (six parts, November and December 2026): the simulations and
  closed forms of the five seams and the whole, 121 sections, 386 unit tests, 33 figures, TLA+ models of each
  seam's formal side (5) and P models of three, a companion page per part with its bill and reversal condition,
  the claim map, 67 falsification criteria, the assumptions, a notation page and a field guide, and
  `audit/seam_audit.py`, which runs the five whole-system tests on a cluster's own objects.

### capacity-in-arrears

- The experiment behind *Capacity in Arrears* (four parts, October 2026): the port of the Kubernetes v1.34.0
  replica calculation with its upstream test cases, the simulations of the scaling loop, the backlog loop, the
  setup-time farm and the overload study, 49 sections, 34 unit tests, 24 figures, a companion page per part,
  the claim map, 14 falsification criteria and the cluster kit.
