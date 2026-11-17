# The formal side, checked with TLC

Each part of the series states its mechanisms' contracts as properties and proves them in isolation.
This folder checks the same properties with TLC, the TLA+ model checker, on small specifications: each
contract on its own, where it holds, and composed, where TLC finds the counterexample. The posts quote
the verdicts in `expected.txt`.

| Specification | Part | Holds alone | Fails composed |
|---|---|---|---|
| `SharedSignal.tla` | 1 | each autoscaler settles, `<>[]Rest`, from 210 starting points | the pair never rests below the band; it rests inside it |
| `NestedPair.tla` | 2 | the pod loop's deadline, and a node loop that sees the final need | the separated deadline; the nested pair meets R (pod + node) |
| `SharedQueue.tla` | 3 | the lists stop with instant service or long history; no 410 under a bounded partition | a storm that never calms; a 410 once a partition outlasts the history |
| `StartCycle.tla` | 4 | every component's guarantee | every component eventually running, with a cycle |
| `AdmissionOrder.tla` | 5 | two webhooks under the contract; five under the orchestrator, every order | three webhooks, reversed, under the contract |

TLC needs Java 11 or later and `tla2tools.jar` (github.com/tlaplus/tlaplus, release 1.8.0):

```
JAVA=/path/to/java TLA2TOOLS=/path/to/tla2tools.jar python3 tla/run.py --check
```

`tests/test_tla.py` runs the same comparison when both are present and skips it otherwise.
