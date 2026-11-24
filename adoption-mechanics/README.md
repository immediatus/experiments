# Adoption Mechanics

The experiment behind the three-post series *Adoption Mechanics* on [e-mindset.space](https://e-mindset.space):
why an organization of people, of AI agents, or of both rejects a design that is correct, and which levers
make adopting it the rational choice.

| Part | Post | What this folder reproduces |
|---|---|---|
| 1 | [Correct, and Rejected](https://e-mindset.space/blog/adoption-mechanics-part1-correct-and-rejected/) | the member model, the sensors, aggregation, hand-off and actuator stages, the write-back loop, the achievable region of six levers on better and worse designs |
| 2 | [Smarter Agents, Fewer Opinions](https://e-mindset.space/blog/adoption-mechanics-part2-smarter-agents-fewer-opinions/) | dependence of model errors on three benchmarks, pooled and within question difficulty, the upgrade condition and its critical elasticity, cascades among correlated peers, mixed panels and when agents help |
| 3 | [The Machine Gets the First Word](https://e-mindset.space/blog/adoption-mechanics-part3-the-machine-gets-the-first-word/) | a model's recall by position, calibrated on six measured models, and reading in parts; mediation for agreement and for difference by speaking order; a debate heard before or after the vote, single advocates and critics; the region of instrument combinations; and instruments that share a source, roles of one model stacked against the floor |

## Check it yourself

```bash
python3 adoption-mechanics/reproduce.py --check            # prints "identical"
python3 adoption-mechanics/reproduce.py --figures --check  # prints "figures identical"
```

## What is where

| Path | What it holds |
|---|---|
| [`model/`](model/) | The member model's stages, standard library only |
| [`tests/`](tests/) | Unit tests of every model function, run by `reproduce.py --check` |
| [`sections/`](sections/) | Sections T1 to T36, listed in [`docs/SECTIONS.md`](docs/SECTIONS.md) |
| [`expected/results.txt`](expected/results.txt) | The frozen output every claim is checked against |
| [`figures/`](figures/) | The six figures of the posts, drawn from the frozen output |
| [`data/`](data/) | Pairwise right/wrong counts, overall and within difficulty strata, for Stanford HELM Lite MMLU and HELM Capabilities GPQA and MMLU-Pro, and the script that fetched them |
| [`docs/`](docs/) | [Claims](docs/CLAIMS.md), [falsification criteria](docs/FALSIFICATION.md), [assumptions](docs/ASSUMPTIONS.md), [sources](docs/SOURCES.md), and a companion page per part |

## Data

The per-question results come from the public bucket of Stanford HELM (Lite and Capabilities). Their licence is not stated, so
the repository stores only counts: for each model its accuracy, and for each pair of models the number of
questions both answered right, one right, the other right, and both wrong, overall and within 5 and 10 strata
of question difficulty. No prompt, question or answer is
stored. `data/fetch_helm.py` refetches them.

## How far to trust it

Every result carries the series' layer tag. **Bound** results are proofs, or facts read from a cited source.
**Fit** results are readings or approximations. **Estimate** results come from these simulations under the
assumptions in [ASSUMPTIONS.md](docs/ASSUMPTIONS.md). The member model's precision and correlation are
calibrated against public peer-review experiments (T22); the career plane's constants are illustrative and
swept (T4). The dependence of model errors is measured from one run per model on three public benchmarks, and
the within-difficulty residual is read against an item-response null with one difficulty per question (T25), a
null that a discrimination per question could refine. **No measured panel of people and agents has been run.**
The falsification criteria say what a run would have to show to refute each part.

## Cite

See the repository's [CITATION.cff](../CITATION.cff). The benchmark counts in [`data/`](data/) derive from
Stanford HELM's public results, which state no licence; only counts are stored.
