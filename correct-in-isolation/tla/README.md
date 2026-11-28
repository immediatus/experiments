# The formal side, checked with TLC

Each part of the series states its mechanisms' contracts as properties and proves them in isolation.
This folder checks the same properties with TLC, the TLA+ model checker, on small specifications: each
contract on its own, where it holds, and composed, where TLC finds the counterexample. The posts quote
the verdicts in `expected.txt`.

| Specification | Part | Holds alone | Fails composed |
|---|---|---|---|
| [`SharedSignal.tla`](SharedSignal.tla) | 1 | each autoscaler settles, `<>[]Rest`, from 210 starting points | the pair never rests below the band; it rests inside it |
| [`NestedPair.tla`](NestedPair.tla) | 2 | the pod loop's deadline, and a node loop that sees the final need | the separated deadline; the nested pair meets R (pod + node) |
| [`SharedQueue.tla`](SharedQueue.tla) | 3 | the lists stop with instant service or long history; no 410 under a bounded partition | a storm that never calms; a 410 once a partition outlasts the history |
| [`StartCycle.tla`](StartCycle.tla) | 4 | every component's guarantee | every component eventually running, with a cycle |
| [`AdmissionOrder.tla`](AdmissionOrder.tla) | 5 | two webhooks under the contract; five under the orchestrator, every order | three webhooks, reversed, under the contract |

TLC needs Java 11 or later and `tla2tools.jar` (github.com/tlaplus/tlaplus, release 1.8.0):

```
JAVA=/path/to/java TLA2TOOLS=/path/to/tla2tools.jar python3 tla/run.py --check
```

[`../tests/test_tla.py`](../tests/test_tla.py) runs the same comparison when both are present and skips it otherwise.

## Files

Each configuration names the constants and the property TLC checks against its specification.

| Specification | Configurations |
|---|---|
| [`SharedSignal.tla`](SharedSignal.tla) | [`band`](SharedSignal_band.cfg), [`horizontal`](SharedSignal_horizontal.cfg), [`pair`](SharedSignal_pair.cfg), [`vertical`](SharedSignal_vertical.cfg) |
| [`NestedPair.tla`](NestedPair.tla) | [`nested`](NestedPair_nested.cfg), [`nested_separated_deadline`](NestedPair_nested_separated_deadline.cfg), [`pod_alone`](NestedPair_pod_alone.cfg), [`separated`](NestedPair_separated.cfg) |
| [`SharedQueue.tla`](SharedQueue.tla) | [`history`](SharedQueue_history.cfg), [`instant`](SharedQueue_instant.cfg), [`net_bounded`](SharedQueue_net_bounded.cfg), [`net_unbounded`](SharedQueue_net_unbounded.cfg), [`one`](SharedQueue_one.cfg), [`storm`](SharedQueue_storm.cfg) |
| [`StartCycle.tla`](StartCycle.tla) | [`acyclic_AllUp`](StartCycle_acyclic_AllUp.cfg), [`acyclic_EveryGuarantee`](StartCycle_acyclic_EveryGuarantee.cfg), [`cycle_AllUp`](StartCycle_cycle_AllUp.cfg), [`cycle_EveryGuarantee`](StartCycle_cycle_EveryGuarantee.cfg) |
| [`AdmissionOrder.tla`](AdmissionOrder.tla) | [`contract2`](AdmissionOrder_contract2.cfg), [`contract3`](AdmissionOrder_contract3.cfg), [`orchestrated5`](AdmissionOrder_orchestrated5.cfg) |

[`run.py`](run.py) checks every configuration and prints one line each; with `--check` it compares them with
[`expected.txt`](expected.txt), the frozen verdicts.
