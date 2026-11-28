# model/

The libraries every section and test uses: the simulations, the ports of documented rules, and the closed forms,
each in one place. No module runs on its own; [`../reproduce.py`](../reproduce.py) and [`../tests/`](../tests/)
call them. Defaults equal the series' specimen, and each public function's docstring names its inputs, outputs
and units.

| Module | What it holds |
|---|---|
| [`admission.py`](admission.py) | A chain of mutating admission webhooks under the documented reinvocation contract. |
| [`audit.py`](audit.py) | Whole-system tests for the seams, and the pairwise tests they replace (Part 6). |
| [`formulas.py`](formulas.py) | Every closed form of the series, one function each, so that every section and test comparing a simulation with a formula uses the same formula. |
| [`formulas_assumption.py`](formulas_assumption.py) | Closed forms of Part 4, a shared assumption: how often a start-time cycle binds, how long a webhook that rejects its own pods lasts, and how long recovery waits on doubling retries. |
| [`formulas_order.py`](formulas_order.py) | Closed forms of Part 5, a shared order: passes an enabling chain needs, the Eulerian share of orders that converge, value and match links, the passes of a general fact graph, and mixed images under per-pod pinning. |
| [`formulas_signal.py`](formulas_signal.py) | Closed forms of Part 1, a shared signal: the gain matrices and relative gains of the paired autoscalers, the rest band and the staircase, the history statistic, the split pairing through the heap, and the tail of usage. |
| [`formulas_state.py`](formulas_state.py) | Closed forms of Part 3, a shared state: the backlog a forced list builds against the history, the client's backoff and the runs of rejections behind a 410, the mean-field fold, and API Priority and Fairness's levels. |
| [`formulas_time.py`](formulas_time.py) | Closed forms of Part 2, a shared time scale: rounds of a nested surge, headroom and its price, the memory of the two scale-down windows, the cost of holding or releasing between surges, and the tail of surge sizes. |
| [`formulas_whole.py`](formulas_whole.py) | Closed forms of Part 6, the whole: symmetric loops whose every proper subset passes while the whole is singular, the spread order of a chain, and the order of the shared state counted in informers. |
| [`gc_data.py`](gc_data.py) | Cycle lower-bound overheads of five OpenJDK 17 collectors, transcribed from Cai, Blackburn, Bond and Maas, "Distilling the Real Cost of Production Garbage Collectors", ISPASS 2022 (doi 10.1109/ISPASS55109.2022.00005), table "Cycle LBOs averaged over 16 benchmarks": the geometric mean, over 16 DaCapo benchmarks, of a lower bound on total CPU cycles relative to the distilled cost without collection, at heap sizes given as multiples of each benchmark's minimum heap. |
| [`hpa_vpa.py`](hpa_vpa.py) | A horizontal and a vertical autoscaler holding the same utilisation metric, each following its documented rule. |
| [`incomplete.py`](incomplete.py) | Part 6: whole-system tests on incomplete descriptions. |
| [`interaction.py`](interaction.py) | Part 6: the order of an interaction, computed for each seam. |
| [`nested.py`](nested.py) | A pod autoscaler nested in a node autoscaler, each following its documented rule. |
| [`percolation.py`](percolation.py) | Part 4's start-time graph at scale. |
| [`ratios.py`](ratios.py) | Part 6: each seam's ratio of what the composite asks to what it can give. |
| [`recovery.py`](recovery.py) | Recovery of replicated components with start-time dependencies. |
| [`relist.py`](relist.py) | Informers re-watching an API server whose overload protection queues them. |
| [`supervisor_whole.py`](supervisor_whole.py) | Part 6: a whole-system supervisor on the two seams that share settings, the signal and the time scale, on the specimen of Parts 1 and 2: 16 pods at a 50% target, limit equal to request, a surge to thirty times the demand they carry. |
| [`tail_buffer.py`](tail_buffer.py) | A buffer controller for Part 2. |
| [`tail_lists.py`](tail_lists.py) | Part 3's tail of list costs. |
