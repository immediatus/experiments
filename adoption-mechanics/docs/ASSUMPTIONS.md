# Assumptions

Each row: what the model assumes, where the input comes from, and what changes if it is wrong.

## Part 1: the human ledger

| Assumption | Source or status | If it is wrong |
|---|---|---|
| Signals are binary with bounded log-likelihood ratio | Model choice; bounded signals are what make cascades possible (Smith and Sørensen) | Unbounded signals end cascades eventually; T3's rates become upper bounds |
| Errors correlate through one shared factor, at a single rho | Model choice, the one-factor (Vasicek) model | Several factors give a floor per factor; the single-factor floor is the case of one dominant shared background |
| Precision 0.7 and correlation 0.25 for the running case | Calibrated against peer review (T22): reliability 0.34 implies 0.70; the NeurIPS committees' disagreement implies a within-review error correlation of 0.23 to 0.32 | Peer review is an analogue of design review (Fit); T23 reruns the case at 0.67 and 0.28, and T10 sweeps both |
| Symmetric precision and symmetric herding | Model choice; the field evidence says otherwise: reviews spot weak proposals better, and experts follow critical scores more readily (Cortes and Lawrence; Lane and coauthors) | T23 adds both asymmetries; the review becomes more cautious and the conclusions hold |
| A member follows the lead once it exceeds their own signal by more than one step | Bikhchandani, Hirshleifer and Welch's rule, myopic | People herd less when observed (March and Ziegelmeyer); T3 adds that as a probing weight |
| Career plane: value of accuracy 0.25, endorsement weight 1.5 | Illustrative constants, swept in T4 | The sign of the endorsed senior's margin turns at T4's swept values; the post reports the region, not a point |
| Groups holding unequal evidence (T26): a pilot team of 5 at precision 0.8 and two groups of 5 at 0.65, deciding apart; a design any group does not favor stops | Illustrative; the mean precision matches the calibrated 0.70, and T26 also splits the evidence 0.70 / 0.70 / 0.70 and 0.90 / 0.60 / 0.60 | How real groups divide evidence is not measured |
| Cross-communication (T27): one owner settles the pairwise disagreements of consulted groups one at a time, each taking an exponential time, within a 13-week window | Illustrative; the mean settling time is swept at 0.5, 1 and 2 weeks | Parallel settling would shorten the time; the count of pairs still grows as the square of the groups |
| Conclusions carried between groups as a public lead of 1 or 2 signals each | Illustrative | How much a group weighs another's conclusion is not measured |
| Extra groups' ideal points between the status quo and the approvers' centroid, with scatter 0.25, 0.5 or 1.0 | Illustrative: a group pulled in late partly favors what it has | The design's chance falls similarly at every scatter swept |
| The law of triviality (T27): each reviewer holds an opinion on a piece with chance 0.2 times the number of pieces to a steepness of 0.5, 0.75 or 1.0 (0 as the control); pairs of holders settle in a quarter of a week each, one at a time; each holder accepts a piece with chance 0.9 | Illustrative, the steepness swept | How the share of opinion holders grows as pieces get simpler is not measured |
| Site reliability's release-readiness check | Not modeled: every approved design ships | A release check would add a stage after the approvals |
| Partitioned groups share the whole correlation | Model choice for the headline numbers | Part of reviewers' shared error is local to their room; T10 also gives divergence with 0.12 of the 0.25 local to each group, which is higher |
| Gates read the tally at face value | Model choice: the actuator compares the net share of endorsements, not its evidential weight, with the threshold | A sequence inflates the tally (T10), which is why a blind poll alone looks cautious |
| Each reporting layer keeps 0.85 of the signal's amplitude | Illustrative, swept in T10 | Adoption at 0.75 and 0.95 is in T10 |
| Gates' ideal points in two dimensions of concern, Euclidean preferences | Model choice; the hull form of Tsebelis's result needs circular indifference curves | With other strictly convex preferences (weighted concerns) the cliff is the gates' Pareto set, which can differ from the hull of the ideal points |
| Hysteresis: merit follows a random walk reviewed at discrete steps; switching cost and loss aversion set the band | Dixit's model, solved by value iteration | The band's exponent depends on the cadence (T6); the post quotes no single exponent |
| Loss aversion 2.25, weighting the periods in which the successor trails the incumbent | Tversky and Kahneman's estimate; placement is a model choice | Placed on the cost of leaving the status quo instead (status-quo bias), it raises the adoption threshold, 0.1771 to 0.2681 at a cost of 0.2 (T6); the running case uses the first placement |
| Hand-off as deterministic attenuation of the verdict against a fixed threshold | Model choice | It lowers adoption of both designs (T10); a hand-off that adds noise per layer would also blur them |
| Stated reasons: a fraction phi follow the true driver, the rest a story biased toward the incumbent | Model choice; human evidence from choice blindness, agent evidence from chain-of-thought faithfulness | A bias that varies across episodes moves the limit but not the existence of a wrong fixed point |

## Part 2: agents and mixed teams

| Assumption | Source or status | If it is wrong |
|---|---|---|
| A benchmark question stands for a review decision | Fit; benchmark items are not design reviews | The measured rho describes models on MMLU; the transfer to reviews is stated as Fit |
| Latent correlation from the tetrachoric correlation of a pair's 2x2 counts | Standard estimator; assumes a bivariate normal latent | phi on the indicators is reported beside it, and is bounded by the Fréchet-Hoeffding limits when accuracies differ |
| Within-difficulty dependence read against a null | An item-response null with one difficulty per question and one ability per model (T25) gives the estimator's own artifact, about 1.15 | A null with a discrimination per question could absorb part of the strongest pairs' residual; it needs per-question records, which are not stored |
| Members predict the crowd from their own answer in the surprisingly-popular rule | Prelec, Seung and McCoy's specification | A static prediction (the earlier version) gave a slightly smaller gap; the dilution holds either way |
| Pooled dependence over questions of varying difficulty | Pooled is the quantity that sets a panel's floor over a question mix; difficulty is the shared factor | Within ten difficulty strata (difficulty from the other models) the Mantel-Haenszel odds ratio is near 1 for most pairs and above 1 for the strongest; strata leave some difficulty inside, so five strata read higher (T13) and an item-response model would refine both |
| Within-stratum dependence by the Mantel-Haenszel odds ratio | Standard for sparse stratified 2x2 tables; a tetrachoric correlation per stratum fails when a stratum has no shared error, which half the strata of the strongest pairs do | Pairs whose pooled odds ratio is not finite are dropped (a handful per benchmark) |
| Three benchmarks, one run per model, chain-of-thought scoring on HELM Capabilities | Data choice; HELM's latest release per model | Another release or decoding setting may move individual pairs; the counts are stored, so the computation can be repeated |
| One run per model and subject, the latest in the HELM Lite bucket | Data choice | Another run of the same model may differ by sampling; counts are stored, so the computation can be repeated |
| Tiers of equal size among models above half accuracy | Analysis choice; the upgrade condition requires p below one half | Other splits are computable from the stored counts |
| Agents in the mixed panel answer the successor with probability 0.3 when blind to the local fact, and 0.3 plus or minus half of agent_info when they carry part of it, correlated at 0.3 or 0.6 | Illustrative: a shared blind spot, and a knob for partial knowledge | T15 reports both states of the local fact; T17 sweeps agent_info and finds where the whole panel beats the people |
| 40% of the people hold the local fact | Illustrative | The people's own gap grows with the informed share; T15 sweeps the number of people |
