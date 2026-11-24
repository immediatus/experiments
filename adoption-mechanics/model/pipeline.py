"""The composed pipeline: sensors, aggregation, hand-off and actuator for one review committee.

Adoption is the product of each stage's survival, so it is additive in log-probability. The running case is
a Committee: members whose binary signals come from the one-factor latent model (sensors.latent_votes), a
champion who speaks first and holds the correct signal, a vote that is sequential with cascades
(cascades.sequence) or simultaneous and blind, a hand-off through reporting layers that keeps a fraction
`candor` of the signal's amplitude per layer, and veto gates. Each gate applies the spatial test (the design
must be strictly preferred to the status quo by every gate's ideal point; none can be when the status quo lies
in the hull of the ideal points, actuator.win_set_nonempty) and an evidence test: the relayed estimate of the
design's merit, plus the gate's own noise, must clear the adopt threshold of the hysteresis band.

Every constant is a field of Committee, with the running case's values as defaults; sections sweep them.
"""
import functools
import math
import random
from dataclasses import dataclass
from statistics import NormalDist

from actuator import hysteresis_band, win_set_nonempty
from cascades import locked, sequence
from sensors import latent_votes

_N = NormalDist()


def adoption_probability(stages: dict[str, float]) -> float:
    """The probability of adoption under Definition 2's product form: the product of each stage's probability of
    passing the design on, from a mapping of stage name to that probability in [0, 1]."""
    out = 1.0
    for v in stages.values():
        out *= v
    return out


def log_odds_ledger(stages: dict[str, float]) -> dict[str, float]:
    """Each stage's contribution to ln P(adopt): ln of its survival (minus infinity at zero)."""
    return {k: (math.log(v) if v > 0.0 else float('-inf')) for k, v in stages.items()}


def lever_value(stages: dict[str, float], stage: str, delta: float) -> float:
    """Gain in adoption from raising one stage's survival by delta (capped at 1): the product of the other
    stages times the rise, so zero whenever another stage is at zero."""
    raised = dict(stages)
    raised[stage] = min(1.0, stages[stage] + delta)
    return adoption_probability(raised) - adoption_probability(stages)


def relayed_information(info: float, candor: float, layers: int) -> float:
    """Information left after `layers` hand-offs that each keep a fraction `candor` of the signal's
    amplitude: info * candor^(2 layers)."""
    return info * candor ** (2 * layers)


def partition_divergence(groups: int, members: int, rho: float, trials: int, seed: int,
                         p: float = 0.3, local: float = 0.0) -> float:
    """Share of trials in which groups holding separate state reach different verdicts. Members are split as
    evenly as possible; each group decides by its own majority (ties count as errors); members err with
    probability p. Two members of one group correlate at rho; `local` of that is a factor drawn separately for
    each group (a room's own frame), so members of different groups correlate at rho - local."""
    if not 0.0 <= local <= rho:
        raise ValueError('local must lie in [0, rho], got %r' % local)
    if groups <= 1:
        return 0.0
    rng = random.Random(seed)
    sizes = [members // groups + (1 if i < members % groups else 0) for i in range(groups)]
    tau = _N.inv_cdf(p)
    a, w, b = math.sqrt(rho - local), math.sqrt(local), math.sqrt(1.0 - rho)
    differ = 0
    for _ in range(trials):
        if local == 0.0:
            votes = latent_votes(members, p, rho, rng)
        else:
            g = rng.gauss(0.0, 1.0)
            votes = []
            for s in sizes:
                h = rng.gauss(0.0, 1.0)
                votes += [a * g + w * h + b * rng.gauss(0.0, 1.0) < tau for _ in range(s)]
        verdicts, start = set(), 0
        for s in sizes:
            part = votes[start:start + s]
            start += s
            verdicts.add(2 * sum(part) >= s)
        if len(verdicts) > 1:
            differ += 1
    return differ / trials


@dataclass(frozen=True)
class SharedInput:
    """One input every member hears, such as a model's report, a debate's verdict or a critic's flag. It says for the
    design with probability p_better when the design is better and p_worse when it is worse, and against it
    otherwise; it is there at all with probability `present`. Members weigh it by its log-likelihood ratio, in
    signals, unless `weight` gives the weight they put on it whatever it is worth (a persuasive source). Heard before
    the vote it is a public lead; with `after` it is added to the tally once the members have acted. Inputs that name
    the same `source` (one model family, however it is prompted) err together: each is right with its own accuracy,
    through a latent score sharing the committee's family_rho with every input of that source; inputs with no source
    (people checking against a ground-truth channel) err independently."""
    p_better: float
    p_worse: float
    after: bool = False
    present: float = 1.0
    weight: float | None = None
    source: str = ''


@dataclass(frozen=True)
class Committee:
    """The running case. Members after the champion err with probability 1 - precision and correlate at rho;
    the champion argues for the design whether or not it is better (design_better);
    merit_scale is the design's true merit advantage in units of the merit walk's step. precision_worse, when set,
    is the members' precision on a worse design (peer review is better at spotting weak proposals than strong ones);
    probe_for and probe_against are the log-odds weights members put on their own signal before following a lead
    for the design or against it (unequal weights model a negativity bias: critical leads are followed sooner).
    debate, when above 0, is the accuracy in (0.5, 1) of a two-sided debate every member hears before acting: its
    verdict enters as a public lead of its log-odds, in signals. With debate_after the members act first, without
    hearing it, and the debate's verdict is added to their tally as one more input weighted by its log-odds in
    signals. advocate_lead is a public lead toward the design,
    in signals, whatever its merit: a single advocate heard first (0: none). inputs is a tuple of SharedInput every
    member hears, drawn after the debate. family_rho is the latent correlation of the errors of two inputs from one
    source, and cross_rho (at most family_rho) that of two inputs from different model sources."""
    members: int = 15
    precision: float = 0.7
    rho: float = 0.25
    cascades: bool = True
    first_speaker_silent: bool = False
    layers: int = 3
    candor: float = 0.85
    merit_scale: float = 1.5
    gate_noise: float = 0.3
    c_switch: float = 0.2
    loss_aversion: float = 2.25
    discount: float = 0.95
    gate_ideals: tuple = ((2.0, 0.5), (1.5, -0.5), (2.5, -0.2), (2.2, 0.8))
    status_quo: tuple = (0.0, 0.0)
    design: tuple = (1.8, 0.1)
    design_better: bool = True
    precision_worse: float | None = None
    probe_for: float = 0.0
    probe_against: float = 0.0
    debate: float = 0.0
    debate_after: bool = False
    advocate_lead: float = 0.0
    inputs: tuple = ()
    family_rho: float = 0.0
    cross_rho: float = 0.0


def _sq(a, b) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _spatial_pass(c: Committee) -> bool:
    if not win_set_nonempty(c.status_quo, list(c.gate_ideals)):
        return False
    return all(_sq(c.design, z) < _sq(c.status_quo, z) for z in c.gate_ideals)


def verdict_margin(c: Committee, rng: random.Random) -> float:
    """One review's verdict margin in [-1, 1]: net endorsements of the design over actions taken, the tally the
    gates read at face value. Members' errors come from the one-factor model (sensors.latent_votes); with
    c.cascades they act in order under the cascade rule of cascades.sequence, otherwise all at once."""
    precision = c.precision if c.design_better or c.precision_worse is None else c.precision_worse
    errs = latent_votes(c.members - 1, 1.0 - precision, c.rho, rng)
    truth = 1 if c.design_better else -1
    others = [-truth if e else truth for e in errs]
    signals = ([] if c.first_speaker_silent else [1]) + others
    lead, after = shared_lead(c, truth, rng)
    if c.cascades:
        acts = sequence(signals, c.precision, c.probe_for, c.probe_against, lead=lead)
    elif lead:
        acts = [sequence([s], c.precision, c.probe_for, c.probe_against, lead=lead)[0] for s in signals]
    else:
        acts = signals
    return (sum(acts) + after) / (len(acts) + abs(after))


def shared_lead(c: Committee, truth: int, rng: random.Random) -> float:
    """The lead every member faces before acting, in signals (a single advocate's, plus a debate verdict's log-odds
    toward the side it found for, right with probability c.debate), and the debate's input to the tally after the
    members act (with c.debate_after, the verdict moves there instead). Draws from rng only when there is a debate."""
    lead, after = c.advocate_lead, 0.0
    if c.debate:
        if not 0.5 < c.debate < 1.0:
            raise ValueError('debate accuracy must lie in (0.5, 1), got %r' % c.debate)
        side = truth if rng.random() < c.debate else -truth
        weight = side * math.log(c.debate / (1.0 - c.debate)) / math.log(c.precision / (1.0 - c.precision))
        if c.debate_after:
            after = weight
        else:
            lead += weight
    step = math.log(c.precision / (1.0 - c.precision))
    factors = {}
    for s in c.inputs:
        if s.present <= 0.0 or (s.present < 1.0 and rng.random() >= s.present):
            continue
        p_for = s.p_better if truth > 0 else s.p_worse
        if s.source and c.family_rho > 0.0 and 0.0 < p_for < 1.0:
            if not 0.0 <= c.cross_rho <= c.family_rho < 1.0:
                raise ValueError('need 0 <= cross_rho <= family_rho < 1, got %r, %r' % (c.cross_rho, c.family_rho))
            if '' not in factors:
                factors[''] = rng.gauss(0.0, 1.0)
            if s.source not in factors:
                factors[s.source] = rng.gauss(0.0, 1.0)
            p_right = p_for if truth > 0 else 1.0 - p_for
            z = (math.sqrt(c.cross_rho) * factors[''] + math.sqrt(c.family_rho - c.cross_rho) * factors[s.source]
                 + math.sqrt(1.0 - c.family_rho) * rng.gauss(0.0, 1.0))
            right = z < _N.inv_cdf(p_right)
            says_for = right if truth > 0 else not right
        else:
            says_for = p_for >= 1.0 or (p_for > 0.0 and rng.random() < p_for)
        if s.weight is not None:
            weight = s.weight * (1 if says_for else -1)
        else:
            num, den = (s.p_better, s.p_worse) if says_for else (1.0 - s.p_better, 1.0 - s.p_worse)
            weight = math.log(max(num, 1e-12) / max(den, 1e-12)) / step
        if s.after:
            after += weight
        else:
            lead += weight
    return lead, after


def _group_signals(c: Committee, k: int, size: int, precision: float, rng: random.Random, g: float, local: float,
                   truth: int) -> list[int]:
    """The signals of group k (+1 for the design): its members' errors share the organization-wide factor g and, when
    local > 0, a factor of the group's own room; the champion speaks first in group 0 unless silent."""
    n = size - 1 if k == 0 else size
    if local == 0.0:
        errs = latent_votes(n, 1.0 - precision, c.rho, rng, shared=g)
    else:
        a, w, b = math.sqrt(c.rho - local), math.sqrt(local), math.sqrt(1.0 - c.rho)
        h, tau = rng.gauss(0.0, 1.0), _N.inv_cdf(1.0 - precision)
        errs = [a * g + w * h + b * rng.gauss(0.0, 1.0) < tau for _ in range(n)]
    return ([1] if k == 0 and not c.first_speaker_silent else []) + [-truth if e else truth for e in errs]


def group_review(c: Committee, groups: tuple, rng: random.Random, local: float = 0.0, carry: float = 0.0,
                 tallies: bool = False, details: bool = False) -> tuple:
    """One review held by groups that decide apart and then exchange only their conclusions. groups is a tuple of
    (members, precision) per group, the first group holding the champion (who speaks first unless
    c.first_speaker_silent); precision is a group's share of the evidence, the chance its members' signals are right.
    Errors share one organization-wide factor and, when local > 0, a factor of each group's own room, local of the
    total latent correlation c.rho. Each group votes in its own sequence (or blind poll, without c.cascades).
    carry is cross-communication: each group votes after hearing the earlier groups' conclusions, and starts its
    sequence with a public lead of carry signals per earlier group, toward that group's conclusion (0: groups that
    do not hear each other). Returns (whether every group's tally favors the design, the net share of endorsements
    over all members), and the groups' tallies as a third item when tallies is set, or, when details is set, a list of
    each group's signals, actions, tally and the index at which its sequence locked into a cascade (None if never).
    A single group of c.members at c.precision reproduces verdict_margin draw for draw."""
    if not 0.0 <= local <= c.rho:
        raise ValueError('local must lie in [0, rho], got %r' % local)
    truth = 1 if c.design_better else -1
    g = rng.gauss(0.0, 1.0)
    favor, acts_all, heard, per_group, info = True, [], 0.0, [], []
    shared, after = shared_lead(c, truth, rng) if (c.inputs or c.debate or c.advocate_lead) else (0.0, 0.0)
    for k, (size, precision) in enumerate(groups):
        signals = _group_signals(c, k, size, precision, rng, g, local, truth)
        lead0 = carry * heard + shared
        if c.cascades:
            acts = sequence(signals, precision, c.probe_for, c.probe_against, lead=lead0)
        elif lead0:
            acts = [sequence([s], precision, c.probe_for, c.probe_against, lead=lead0)[0] for s in signals]
        else:
            acts = signals
        tally = sum(acts)
        if details:
            lock, lead, step = None, lead0, math.log(precision / (1.0 - precision))
            for i, sg in enumerate(signals if c.cascades else []):
                if locked(lead, step, c.probe_for if lead > 0 else c.probe_against):
                    lock = i
                    break
                lead += sg
            info.append({'signals': signals, 'acts': acts, 'tally': tally, 'lock': lock})
        favor = favor and tally > 0
        heard += (tally > 0) - (tally < 0)
        acts_all += acts
        per_group.append(tally)
    out = (favor, (sum(acts_all) + after) / (len(acts_all) + abs(after)))
    if details:
        return out + (info,)
    return out + (per_group,) if tallies else out


def pooled_review(c: Committee, groups: tuple, rng: random.Random, local: float = 0.0,
                  weights: str = 'equal') -> tuple[bool, float]:
    """One review whose groups vote blind and pool their evidence instead of exchanging conclusions: the errors are
    drawn as in group_review, every member acts on their own signal, and the review favors the design when the
    pooled tally is positive. weights 'equal' counts every member once; 'reliability' counts each member of a group
    by the log-odds of its precision, ln(q / (1 - q)), the weight an informed decision maker gives that evidence.
    Returns (whether the pooled tally favors the design, the weighted net share of endorsements in [-1, 1]).
    One group with weights 'equal' reproduces group_review's blind review draw for draw."""
    if weights not in ('equal', 'reliability'):
        raise ValueError('weights must be equal or reliability, got %r' % weights)
    if not 0.0 <= local <= c.rho:
        raise ValueError('local must lie in [0, rho], got %r' % local)
    truth = 1 if c.design_better else -1
    g = rng.gauss(0.0, 1.0)
    total = mass = 0.0
    shared, after = shared_lead(c, truth, rng) if (c.inputs or c.debate or c.advocate_lead) else (0.0, 0.0)
    for k, (size, precision) in enumerate(groups):
        signals = _group_signals(c, k, size, precision, rng, g, local, truth)
        if shared:
            signals = [sequence([s], precision, c.probe_for, c.probe_against, lead=shared)[0] for s in signals]
        weight = 1.0 if weights == 'equal' else math.log(precision / (1.0 - precision))
        total += weight * sum(signals)
        mass += weight * len(signals)
    if after:
        unit = math.log(c.precision / (1.0 - c.precision))
        total += after * unit
        mass += abs(after) * unit
    return total > 0, total / mass


def _erlang_survival(channels: int, window: float, mean_settle: float) -> float:
    x = window / mean_settle
    term, terms = math.exp(-x), []
    for j in range(channels):
        terms.append(term)
        term *= x / (j + 1)
    return 1.0 - math.fsum(terms)


def window_survival(groups: int, window: float, mean_settle: float) -> float:
    """The chance a review consulting `groups` groups decides before its window closes, when one decision owner
    settles the groups' pairwise disagreements one at a time: groups (groups - 1) / 2 channels, each taking an
    exponential time with mean mean_settle (the units of window). The total is Erlang, so the chance is
    1 - sum over j below the channel count of exp(-x) x^j / j!, with x = window / mean_settle."""
    return _erlang_survival(groups * (groups - 1) // 2, window, mean_settle)


def bikeshed(pieces: int, trials: int, seed: int, reviewers: int = 15, share_whole: float = 0.2,
             steepness: float = 0.75, accept: float = 0.9, window: float = 13.0,
             mean_settle: float = 0.25) -> tuple[float, float, float]:
    """The law of triviality, for a design reviewed as `pieces` pieces. Each of `reviewers` holds an opinion on a
    piece with chance min(0.95, share_whole * pieces ** steepness): a few experts on the whole design, more people
    as the pieces get simpler (steepness 0: the share does not change). Every pair of opinion holders on a piece
    must settle their disagreement, one at a time, each taking an exponential time of mean mean_settle, within the
    window; every opinion holder accepts their piece with chance `accept`. Returns, averaged over trials drawn from
    seed: (the chance the review decides in time, the chance every holder accepts every piece, the chance of both)."""
    share = min(0.95, share_whole * pieces ** steepness)
    rng = random.Random(seed)
    decides = accepted = both = 0.0
    for _ in range(trials):
        holders = [sum(rng.random() < share for _ in range(reviewers)) for _ in range(pieces)]
        w = _erlang_survival(sum(h * (h - 1) // 2 for h in holders), window, mean_settle)
        a = accept ** sum(holders)
        decides += w
        accepted += a
        both += w * a
    return decides / trials, accepted / trials, both / trials


def veto_crowding(extra: int, trials: int, seed: int, spread: float = 0.5, c: Committee | None = None) -> tuple[float, float]:
    """What `extra` more groups with a veto do to the running case's spatial test: (share of draws in which the
    status quo lies in the hull of all the approvers' ideal points, share in which every approver prefers the
    design to the status quo). Each extra group's ideal point lies a uniform share of the way from the status quo
    to the existing approvers' centroid, plus normal scatter of standard deviation `spread` in each direction: a
    group pulled in late cares partly about keeping what it has."""
    c = c or Committee()
    base = list(c.gate_ideals)
    cx, cy = math.fsum(z[0] for z in base) / len(base), math.fsum(z[1] for z in base) / len(base)
    sq, rng = c.status_quo, random.Random(seed)
    inside = passes = 0
    for _ in range(trials):
        gates = list(base)
        for _ in range(extra):
            u = rng.random()
            gates.append((sq[0] + u * (cx - sq[0]) + rng.gauss(0.0, spread), sq[1] + u * (cy - sq[1]) + rng.gauss(0.0, spread)))
        trapped = not win_set_nonempty(sq, gates)
        inside += trapped
        passes += (not trapped) and all(_sq(c.design, z) < _sq(sq, z) for z in gates)
    return inside / trials, passes / trials


def review_traces(c: Committee, trials: int, seed: int, groups: tuple | None = None, local: float = 0.0,
                  carry: float = 0.0) -> list[dict]:
    """Every draw of the reviews stage_fates counts, review by review, from the same seed and in the same order:
    for each review, its groups (signals, actions, tally, where the sequence locked), whether the review favors the
    design, the net share of endorsements, the verdict as relayed through each hand-off (first entry unweakened), each
    approver's noise, the adoption threshold, the approvers who prefer the status quo to the design (their indices),
    and the fate: 'review', 'handoff', 'approvals' or 'adopted'. Without groups, one room of c.members."""
    spatial = _spatial_pass(c)
    vetoes = [i for i, z in enumerate(c.gate_ideals) if not _sq(c.design, z) < _sq(c.status_quo, z)]
    adopt = _adopt_threshold(c.c_switch, c.loss_aversion, c.discount)
    rng = random.Random(seed)
    one_room = groups is None
    if one_room:
        precision = c.precision if c.design_better or c.precision_worse is None else c.precision_worse
        groups = ((c.members, precision),)
    out = []
    for _ in range(trials):
        favor, margin, info = group_review(c, groups, rng, local, carry, details=True)
        if one_room:
            favor = True
        noise = [rng.gauss(0.0, c.gate_noise) for _ in c.gate_ideals]
        full = margin * c.merit_scale
        relayed = [full * c.candor ** d for d in range(c.layers + 1)]
        if favor and spatial and all(relayed[-1] + z > adopt for z in noise):
            fate = 'adopted'
        elif not favor or margin <= 0.0:
            fate = 'review'
        elif spatial and all(full + z > adopt for z in noise):
            fate = 'handoff'
        else:
            fate = 'approvals'
        out.append({'groups': info, 'favor': favor, 'margin': margin, 'relayed': relayed, 'noise': noise,
                    'threshold': adopt, 'vetoes': vetoes, 'fate': fate})
    return out


def stage_fates(c: Committee, trials: int, seed: int, groups: tuple | None = None,
                local: float = 0.0, carry: float = 0.0, pool: str | None = None) -> dict[str, float]:
    """Where each of `trials` reviews of the design ends: the share that dies in the review (its verdict does not
    favor the design), in the hand-off (the unweakened verdict would have cleared every approver, the relayed one
    does not), at the approvals (the spatial test fails, or the verdict fails even unweakened), and the share
    adopted. Without groups the review is one room, as committee_run reviews it; with groups (see group_review) a
    group that does not favor the design stops it there, and carry passes to group_review. With pool ('equal' or
    'reliability') the groups vote blind and pool their evidence instead (pooled_review), and the review stops the
    design when the pooled tally does not favor it."""
    spatial = _spatial_pass(c)
    adopt = _adopt_threshold(c.c_switch, c.loss_aversion, c.discount)
    keep = c.candor ** c.layers
    rng = random.Random(seed)
    out = {'review': 0, 'handoff': 0, 'approvals': 0, 'adopted': 0}
    for _ in range(trials):
        if groups is None:
            favor, margin = True, verdict_margin(c, rng)
        elif pool:
            favor, margin = pooled_review(c, groups, rng, local, pool)
        else:
            favor, margin = group_review(c, groups, rng, local, carry)
        noise = [rng.gauss(0.0, c.gate_noise) for _ in c.gate_ideals]
        full = margin * c.merit_scale
        if favor and spatial and all(full * keep + z > adopt for z in noise):
            out['adopted'] += 1
        elif not favor or margin <= 0.0:
            out['review'] += 1
        elif spatial and all(full + z > adopt for z in noise):
            out['handoff'] += 1
        else:
            out['approvals'] += 1
    return {k: v / trials for k, v in out.items()}


@functools.lru_cache(maxsize=None)
def _adopt_threshold(c_switch: float, loss_aversion: float, discount: float) -> float:
    return hysteresis_band(c_switch, loss_aversion, 1.0, discount)[1]


def committee_run(c: Committee, trials: int, seed: int) -> float:
    """Probability that the committee adopts the design (better or worse, as design_better says): the spatial test, then per trial the
    verdict margin relayed through the layers and judged by every gate against the adopt threshold."""
    if not _spatial_pass(c):
        return 0.0
    adopt = _adopt_threshold(c.c_switch, c.loss_aversion, c.discount)
    rng = random.Random(seed)
    keep = c.candor ** c.layers
    adopted = 0
    for _ in range(trials):
        estimate = verdict_margin(c, rng) * keep * c.merit_scale
        if all(estimate + rng.gauss(0.0, c.gate_noise) > adopt for _ in c.gate_ideals):
            adopted += 1
    return adopted / trials


def frontier(points: list[tuple[float, float]]) -> list[int]:
    """Indices of the undominated operating points (A+, A-): no other point has at least the same A+ and at most
    the same A-, one of them strictly. Of equal points, the first is kept."""
    keep = []
    for i, (gi, bi) in enumerate(points):
        dominated = any((gj >= gi and bj <= bi and (gj > gi or bj < bi)) or ((gj, bj) == (gi, bi) and j < i)
                        for j, (gj, bj) in enumerate(points) if j != i)
        if not dominated:
            keep.append(i)
    return keep
