"""Sections of Post 2, scaling to agents and the blueprint: T11 to T21, T24, T25, T38; and the calibration of Post 1: T22,
T23."""
import functools
import math
import os
import random
from statistics import median

from calibration import committee_reliability, disagreement, error_correlation, panel_agreement, precision_from_icc, shared_from_disagreement
from cascades import cascade_share, public_lead
from correlation import load_counts, mantel_haenszel, phi_from_counts, tetrachoric_from_counts
from hybrid import dilution_bound, dilution_limit, panel_run
from irt import null_within_odds
from pipeline import Committee, committee_run, frontier
from sensors import error_floor, latent_votes, majority_error
from upgrade import critical_elasticity, upgrade_improves, upgrade_margin

TRIALS = 20000
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'model_errors.json')
DATA_GPQA = os.path.join(os.path.dirname(DATA), 'model_errors_gpqa.json')
DATA_PRO = os.path.join(os.path.dirname(DATA), 'model_errors_mmlu_pro.json')


@functools.lru_cache(maxsize=None)
def _pairs(path: str = DATA, groups: str = '10') -> tuple[dict, dict, list]:
    """(record, accuracies, [(a, b, latent rho, phi, pooled odds ratio, within odds ratio, its log standard
    error)]) for every pair whose pooled and within-difficulty odds ratios are finite, with `groups` difficulty
    strata. Cached: several sections read the same benchmark, and callers must not change what it returns."""
    rec = load_counts(path)
    acc = {m: v['accuracy'] for m, v in rec['models'].items()}
    out = []
    for key, c in sorted(rec['pairs'].items()):
        a, b = key.split('|')
        counts = (c['n11'], c['n10'], c['n01'], c['n00'])
        if c['n10'] * c['n01'] == 0 or c['n11'] * c['n00'] == 0:
            continue
        try:
            rho = tetrachoric_from_counts(*counts)
            within, se = mantel_haenszel(rec['strata']['pairs'][key][groups])
        except ValueError:
            continue
        pooled = c['n11'] * c['n00'] / (c['n10'] * c['n01'])
        out.append((a, b, rho, phi_from_counts(*counts), pooled, within, se))
    return rec, acc, out


def _quintiles(acc: dict, pairs: list) -> list[list[tuple]]:
    """The pairs as rows (pair mean accuracy, latent rho, phi, pooled odds ratio, within odds ratio, its log
    standard error), sorted by mean accuracy and split into five groups of equal size, the last taking the rest."""
    rows = sorted(((acc[x[0]] + acc[x[1]]) / 2,) + x[2:] for x in pairs)
    q = len(rows) // 5
    return [rows[i * q:(i + 1) * q] if i < 4 else rows[4 * q:] for i in range(5)]


def t11():
    print('T11 a synthetic upgrade path: each member\'s error p falls while the latent correlation of members\' '
          'errors rises; p | rho | large-panel floor | margin of the step from the row above (positive: the '
          'panel improves) | improves | elasticity of correlation with respect to error over the step, '
          '-d ln rho / d ln p | the critical elasticity of Corollary 1 at the step\'s geometric mean error')
    path = ((0.30, 0.10), (0.25, 0.20), (0.20, 0.35), (0.15, 0.50), (0.10, 0.65))
    prev = None
    for p, rho in path:
        if prev is None:
            print('  %.2f | %.2f | %.4f | - | -' % (p, rho, error_floor(p, rho)))
        else:
            el = -math.log(rho / prev[1]) / math.log(p / prev[0])
            mid = math.sqrt(p * prev[0])
            print('  %.2f | %.2f | %.4f | %+.4f | %s | elasticity %.2f | critical %.2f'
                  % (p, rho, error_floor(p, rho), upgrade_margin(*prev, p, rho),
                     'yes' if upgrade_improves(*prev, p, rho) else 'no', el, critical_elasticity(mid)))
        prev = (p, rho)


def t12():
    print('T12 measured: Stanford HELM Lite MMLU, models above 50% accuracy, split by accuracy into four tiers '
          'of equal size; within each tier the mean error, the mean latent (tetrachoric) and indicator (phi) '
          'correlation over its pairs, the median Mantel-Haenszel odds ratio of shared errors within 10 strata of '
          'question difficulty, the large-panel floor of a majority drawn from the tier, the ceiling of an average '
          'of latent scores 1/rho and of votes 1/phi; then each upgrade from one tier to the next, with the '
          'elasticity of correlation with respect to error against the critical elasticity')
    rec, acc, pairs = _pairs()
    strong = sorted((m for m in acc if acc[m] > 0.5), key=lambda m: acc[m])
    k = len(strong) // 4
    tiers = [strong[i * k:(i + 1) * k] if i < 3 else strong[3 * k:] for i in range(4)]
    rows = []
    for i, tier in enumerate(tiers):
        members = set(tier)
        inside = [x for x in pairs if x[0] in members and x[1] in members]
        p = 1.0 - math.fsum(acc[m] for m in tier) / len(tier)
        rho = math.fsum(x[2] for x in inside) / len(inside)
        phi = math.fsum(x[3] for x in inside) / len(inside)
        within = median(x[5] for x in inside)
        rows.append((p, rho))
        print('  tier %d | %d models | accuracy %.3f-%.3f | mean error %.4f | latent rho %.4f | phi %.4f | '
              'within-difficulty odds ratio %.2f | floor %.4f | ceiling of scores %.2f | ceiling of votes %.2f'
              % (i + 1, len(tier), acc[tier[0]], acc[tier[-1]], p, rho, phi, within, error_floor(p, rho),
                 1.0 / rho, 1.0 / phi))
    for i in range(3):
        (p0, r0), (p1, r1) = rows[i], rows[i + 1]
        el = -math.log(r1 / r0) / math.log(p1 / p0)
        print('  upgrade tier %d to %d | margin %+.4f | improves %s | member error falls %.1f%% | floor falls '
              '%.1f%% | elasticity %.2f | critical %.2f'
              % (i + 1, i + 2, upgrade_margin(p0, r0, p1, r1), 'yes' if upgrade_improves(p0, r0, p1, r1) else 'no',
                 100 * (1 - p1 / p0), 100 * (1 - error_floor(p1, r1) / error_floor(p0, r0)), el,
                 critical_elasticity(math.sqrt(p0 * p1))))
    print('  data | %d models, %d questions, difficulty strata %s, %s'
          % (len(rec['models']), rec['items'], ' and '.join(str(g) for g in rec['strata']['groups']), rec['licence']))


def _dependence_rows(path: str) -> list[tuple]:
    """Per fifth of pairs by mean accuracy: (lowest and highest mean accuracy, pairs, mean latent rho, mean phi,
    median pooled odds ratio, median within-difficulty odds ratio with 10 strata, share of pairs whose 95% interval
    for it lies above 1, ceiling of votes 1/phi)."""
    _, acc, pairs10 = _pairs(path, '10')
    out = []
    for seg in _quintiles(acc, pairs10):
        phi = math.fsum(x[2] for x in seg) / len(seg)
        above = sum(1 for x in seg if math.log(x[4]) - 1.96 * x[5] > 0) / len(seg)
        out.append((seg[0][0], seg[-1][0], len(seg), math.fsum(x[1] for x in seg) / len(seg), phi,
                    median(x[3] for x in seg), median(x[4] for x in seg), above, 1.0 / phi))
    return out


def t13():
    print('T13 measured, Stanford HELM Lite MMLU: dependence of two models\' errors by the pair\'s mean accuracy '
          '(all pairs with finite odds ratios, quintiles of equal size): accuracy range | pairs | mean latent rho | '
          'mean phi | median pooled odds ratio of shared errors | median Mantel-Haenszel odds ratio within 10 strata '
          'of question difficulty | share of pairs whose 95% interval for it lies above 1 | ceiling of votes 1/phi; '
          'then the within-difficulty median with 5 strata')
    for r in _dependence_rows(DATA):
        print('  %.3f-%.3f | %d | %.4f | %.4f | %.2f | %.2f | %.2f | %.2f' % r)
    _, acc, pairs5 = _pairs(DATA, '5')
    print('  5 strata | ' + ' | '.join('%.2f' % median(x[4] for x in seg) for seg in _quintiles(acc, pairs5)))


def t14():
    print('T14 cascades among correlated peers against a blind vote: signal precision 0.7, by latent correlation '
          'of the signals: share of 30-member runs ending in a wrong cascade, myopic (probing 0), probing 1.0 '
          'and 2.0 log-odds; the error of a blind simultaneous majority of the same 30 (a tie counts as wrong) and of 31; '
          'and the large-panel floor; 20,000 runs, seed 1')
    for rho in (0.0, 0.3, 0.6, 0.75):
        print('  rho %.2f | myopic %.4f | probing %.4f | probing 2.0 %.4f | blind 30 %.4f | blind 31 %.4f | floor %.4f'
              % (rho, cascade_share(30, 0.7, 0.0, TRIALS, 1, rho=rho), cascade_share(30, 0.7, 1.0, TRIALS, 1, rho=rho),
                 cascade_share(30, 0.7, 2.0, TRIALS, 1, rho=rho),
                 majority_error(30, 0.3, rho, TRIALS, 1), majority_error(31, 0.3, rho, TRIALS, 1),
                 error_floor(0.3, rho) if rho > 0 else 0.0))


def t15():
    print('T15 mixed panels on both states of the local fact: 20 agents who answer the successor with probability '
          '0.3 whatever the truth (a shared blind spot) and a number of people of whom 40% hold the local fact; '
          'for the majority, the surprisingly-popular rule and a static threshold at the share the incumbent world '
          'predicts, and the majority of the people alone: adoption when the successor is better (A+) | when it '
          'is worse (A-); by agents\' correlation and '
          'whether agents model the crowd; 8,000 trials, seed 3')
    for rho in (0.3, 0.6):
        for crowd in (True, False):
            for people in (0, 2, 5, 10):
                pp = 0.4 if people else 0.0
                yes = panel_run(people, 20, pp, rho, crowd, 8000, 3, truth=1)
                no = panel_run(people, 20, pp, rho, crowd, 8000, 3, truth=0)
                print('  agent rho %.1f | agents model crowd %s | people %d | majority %.4f %.4f | surprisingly '
                      'popular %.4f %.4f | threshold %.4f %.4f | people alone %.4f %.4f'
                      % (rho, 'yes' if crowd else 'no', people, yes['majority'], no['majority'],
                         yes['surprisingly_popular'], no['surprisingly_popular'], yes['threshold'], no['threshold'],
                         yes['people'], no['people']))


SINGLE = (
    ('reversible pilot: switching cost 0.02', 'actuator', {'c_switch': 0.02}),
    ('one exterior gate removed', 'actuator', {'gate_ideals': ((2.0, 0.5), (1.5, -0.5), (2.5, -0.2))}),
    ('blind simultaneous poll', 'aggregation', {'cascades': False}),
    ('champion insured: speaks first', 'aggregation', {'first_speaker_silent': False}),
    ('decorrelated panel: rho 0.10', 'sensors', {'rho': 0.10}),
    ('flatter chain: 2 layers', 'hand-off', {'layers': 2}),
)


def t16():
    print('T16 each lever alone, from the running case baseline (champion silent, sequential vote): lever | stage it '
          'acts on | adoption of a better design | of a worse design | gap; then the blind poll and the insured champion '
          'together; then the same single levers with the status quo inside '
          'the gates\' hull (2.0, 0.2), where the spatial test fails before any evidence is read; 20,000 trials, '
          'seed 1')
    base = {'first_speaker_silent': True}
    good = committee_run(Committee(**base), TRIALS, 1)
    bad = committee_run(Committee(design_better=False, **base), TRIALS, 1)
    print('  baseline | - | %.4f | %.4f | %.4f' % (good, bad, good - bad))
    for name, stage, change in SINGLE:
        kw = dict(base, **change)
        good = committee_run(Committee(**kw), TRIALS, 1)
        bad = committee_run(Committee(design_better=False, **kw), TRIALS, 1)
        print('  %s | %s | %.4f | %.4f | %.4f' % (name, stage, good, bad, good - bad))
    kw = dict(base, cascades=False, first_speaker_silent=False)
    good = committee_run(Committee(**kw), TRIALS, 1)
    bad = committee_run(Committee(design_better=False, **kw), TRIALS, 1)
    print('  blind poll and insured champion together | aggregation | %.4f | %.4f | %.4f' % (good, bad, good - bad))
    for name, _stage, change in SINGLE:
        kw = dict(base, status_quo=(2.0, 0.2), **change)
        print('  status quo in hull | %s | %.4f' % (name, committee_run(Committee(**kw), TRIALS, 1)))


def t17():
    print('T17 when agents help a mixed panel: five people (40% hold the local fact) and twenty agents who model the '
          'crowd, whose answers move toward the truth by agent_info (0: a blind spot), correlated at 0.3 or 0.6; gap '
          'between adoption when the fact favours the successor and when it opposes it, for the people alone, the '
          'whole panel at the midpoint threshold, and the surprisingly-popular rule; 8,000 trials, seed 3')
    for rho in (0.3, 0.6):
        for info in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
            yes = panel_run(5, 20, 0.4, rho, True, 8000, 3, truth=1, agent_info=info)
            no = panel_run(5, 20, 0.4, rho, True, 8000, 3, truth=0, agent_info=info)
            print('  agent rho %.1f | agent_info %.1f | people alone %.4f | whole panel, midpoint %.4f | surprisingly '
                  'popular %.4f' % (rho, info, yes['people'] - no['people'], yes['midpoint'] - no['midpoint'],
                                    yes['surprisingly_popular'] - no['surprisingly_popular']))


FRONTIER_LEVERS = (
    ('pilot', {'c_switch': 0.02}),
    ('gate', {'gate_ideals': ((2.0, 0.5), (1.5, -0.5), (2.5, -0.2))}),
    ('poll', {'cascades': False}),
    ('champion', {'first_speaker_silent': False}),
    ('decorrelate', {'rho': 0.10}),
    ('layers', {'layers': 2}),
)


def t18():
    print('T18 the achievable region of the running case: every combination of the six levers from the baseline '
          '(champion silent, sequential vote): levers | adoption of a better design | of a worse design | gap | on '
          'the frontier (no other combination adopts a better design at least as often and a worse one at most as '
          'often, one strictly); 20,000 trials, seed 1')
    points, names = _region({})
    combos = ['+'.join(chosen) or 'baseline' for chosen in names]
    keep = set(frontier(points))
    allsix = {'first_speaker_silent': True, 'status_quo': (2.0, 0.2)}
    for _, change in FRONTIER_LEVERS:
        allsix.update(change)
    print('  status quo inside the hull, all six levers | %.4f | %.4f'
          % (committee_run(Committee(**allsix), TRIALS, 1), committee_run(Committee(design_better=False, **allsix), TRIALS, 1)))
    for name, (g, b), i in sorted(zip(combos, points, range(len(points))), key=lambda t: (t[1][1], -t[1][0])):
        print('  %s | %.4f | %.4f | %.4f | %s' % (name, g, b, g - b, 'frontier' if i in keep else '-'))


def t19():
    print('T19 measured on two further benchmarks of current models, Stanford HELM Capabilities GPQA (main) and '
          'MMLU-Pro, chain-of-thought correctness: by the pair\'s mean accuracy (quintiles of pairs): accuracy range | '
          'pairs | mean latent rho | mean phi | median pooled odds ratio | median within-difficulty odds ratio (10 '
          'strata) | share of pairs whose interval lies above 1 | ceiling of votes 1/phi')
    for label, path in (('GPQA', DATA_GPQA), ('MMLU-Pro', DATA_PRO)):
        rec = load_counts(path)
        print('  %s | %d models, %d questions' % (label, len(rec['models']), rec['items']))
        for r in _dependence_rows(path):
            print('  %s | %.3f-%.3f | %d | %.4f | %.4f | %.2f | %.2f | %.2f | %.2f' % ((label,) + r))


def _region(extra: dict) -> tuple[list[tuple[float, float]], list[list[str]]]:
    """Every combination of FRONTIER_LEVERS applied to the baseline (champion silent) with the Committee fields in
    `extra` changed: ([(adoption of a better design, of a worse one)], [names of the levers applied]), in the
    order of the combination's bit mask, so index 0 is the baseline and the last index all six levers."""
    points, names = [], []
    for mask in range(1 << len(FRONTIER_LEVERS)):
        kw = {'first_speaker_silent': True}
        kw.update(extra)
        chosen = []
        for i, (name, change) in enumerate(FRONTIER_LEVERS):
            if mask >> i & 1:
                kw.update(change)
                chosen.append(name)
        points.append((committee_run(Committee(**kw), TRIALS, 1),
                       committee_run(Committee(design_better=False, **kw), TRIALS, 1)))
        names.append(chosen)
    return points, names


def t20():
    print('T20 robustness of the achievable region: the region of T18 recomputed with one constant of the running case '
          'changed at a time: setting | frontier points | of them with the decorrelated panel | the widest-gap combination '
          '| its adoption of a better and a worse design; then each frontier point without the decorrelated panel; '
          '20,000 trials, seed 1')
    settings = (('default', {}), ('precision 0.6', {'precision': 0.6}), ('precision 0.8', {'precision': 0.8}),
                ('rho 0.5', {'rho': 0.5}), ('gate noise 0.5', {'gate_noise': 0.5}), ('merit 1.0', {'merit_scale': 1.0}),
                ('candor 0.75', {'candor': 0.75}))
    for label, extra in settings:
        points, names = _region(extra)
        keep = frontier(points)
        best = max(range(len(points)), key=lambda i: points[i][0] - points[i][1])
        print('  %s | %d | %d | %s | %.4f | %.4f' % (label, len(keep), sum('decorrelate' in names[i] for i in keep),
                                                    '+'.join(names[best]), points[best][0], points[best][1]))
        for i in keep:
            if 'decorrelate' not in names[i]:
                print('  %s | without decorrelation | %s | %.4f | %.4f'
                      % (label, '+'.join(names[i]) or 'baseline', points[i][0], points[i][1]))


def t21():
    print('T21 is the strongest pairs\' residual label noise? the median within-difficulty odds ratio (10 strata) by fifth of '
          'pairs, with all strata, without the hardest tenth of questions, and without the hardest fifth; and the share '
          'of shared mistakes that fall in the hardest tenth')
    for label, path in (('MMLU', DATA), ('GPQA', DATA_GPQA), ('MMLU-Pro', DATA_PRO)):
        rec = load_counts(path)
        acc = {m: v['accuracy'] for m, v in rec['models'].items()}
        rows = []
        for key, c in rec['pairs'].items():
            if c['n10'] * c['n01'] == 0 or c['n11'] * c['n00'] == 0:
                continue
            a, b = key.split('|')
            cells = rec['strata']['pairs'][key]['10']
            try:
                full, without1, without2 = (mantel_haenszel(cells)[0], mantel_haenszel(cells[1:])[0],
                                            mantel_haenszel(cells[2:])[0])
            except ValueError:
                continue
            rows.append(((acc[a] + acc[b]) / 2, full, without1, without2, cells))
        rows.sort(key=lambda r: r[0])
        q = len(rows) // 5
        for name, seg in (('weakest', rows[:q]), ('middle', rows[2 * q:3 * q]), ('strongest', rows[4 * q:])):
            hardest = sum(r[4][0][3] for r in seg) / sum(sum(cell[3] for cell in r[4]) for r in seg)
            print('  %s | %s | all %.2f | without hardest tenth %.2f | without hardest fifth %.2f | hardest tenth\'s share '
                  '%.2f' % (label, name, median(r[1] for r in seg), median(r[2] for r in seg), median(r[3] for r in seg),
                            hardest))


ICC_META = 0.34       # mean inter-reviewer reliability of journal peer review (Bornmann, Mutz and Daniel 2010)
ACCEPT = 0.227        # NeurIPS 2021 acceptance rate across the duplicated papers
OBSERVED = (('NeurIPS 2021', 0.23), ('NeurIPS 2014', 0.259))   # share of duplicated papers the two committees split on


def t22():
    print('T22 calibration against peer review: reviewer precision implied by a reliability; two independent committees '
          'of k reviewers predicted to disagree at acceptance %.3f, against the NeurIPS consistency experiments; the '
          'within-committee shared variance the observed disagreement implies; the latent correlation of two '
          'reviewers\' errors in one committee (200,000 trials, seed 2); and two panels of 15 judging the same proposal, '
          'blind or sequential (reliability %.2f, shared 0.10, 20,000 trials, seed 5)' % (ACCEPT, ICC_META))
    for r in (0.17, 0.23, ICC_META):
        print('  reliability %.2f | precision %.4f' % (r, precision_from_icc(r)))
    for k in (3, 4):
        print('  predicted from reliability %.2f, k %d | committee reliability %.4f | disagreement %.4f'
              % (ICC_META, k, committee_reliability(ICC_META, k), disagreement(committee_reliability(ICC_META, k), ACCEPT)))
    for label, d in OBSERVED:
        for k in (3, 4):
            c = shared_from_disagreement(ICC_META, k, d, ACCEPT)
            print('  observed %s %.3f, k %d | shared variance %.4f' % (label, d, k, c))
    fitted = [shared_from_disagreement(ICC_META, k, OBSERVED[0][1], ACCEPT) for k in (3, 4)]
    for c in [0.0] + fitted:
        print('  shared %.4f | latent error correlation %.4f' % (c, error_correlation(ICC_META, c, 200000, 2)))
    for seq in (False, True):
        within, between = panel_agreement(seq, ICC_META, 0.10, 15, TRIALS, 5)
        print('  %s | within-panel agreement %.4f | panels agree %.4f' % ('sequential' if seq else 'blind', within, between))


CALIBRATED = (
    ('default: precision 0.70, rho 0.25', {}),
    ('calibrated sensors: precision 0.67, rho 0.28', {'precision': 0.67, 'rho': 0.28}),
    ('plus sharper rejection: precision on a worse design 0.72', {'precision': 0.67, 'rho': 0.28, 'precision_worse': 0.72}),
    ('plus negativity bias: weight 1.0 before following a favourable lead', {'precision': 0.67, 'rho': 0.28, 'probe_for': 1.0}),
    ('all three', {'precision': 0.67, 'rho': 0.28, 'precision_worse': 0.72, 'probe_for': 1.0}),
)


def t23():
    print('T23 the running case at calibrated constants: setting | baseline adoption of a better and a worse design | all '
          'six levers | the widest-gap combination | frontier points, of them with the decorrelated panel | cost of a '
          'silent champion with sequential voting minus with a blind poll (better design); 20,000 trials, seed 1')
    for label, extra in CALIBRATED:
        points, names = _region(extra)
        keep = frontier(points)
        base, six = points[0], points[-1]
        best = max(range(len(points)), key=lambda i: points[i][0] - points[i][1])

        def adopt(silent, cascades, extra=extra):
            return committee_run(Committee(first_speaker_silent=silent, cascades=cascades, **extra), TRIALS, 1)
        inter = (adopt(False, True) - adopt(True, True)) - (adopt(False, False) - adopt(True, False))
        print('  %s | %.4f %.4f | %.4f %.4f | %s | %d, %d | %+.4f'
              % (label, base[0], base[1], six[0], six[1], '+'.join(names[best]), len(keep),
                 sum('decorrelate' in names[i] for i in keep), inter))


def t24():
    print('T24 why a sequence and a blind vote err alike at high correlation: 30 members, precision 0.7, signal correlation '
          '0.75, by the shared factor z (low z misleads): range of z | share of trials | sequence wrong | blind majority '
          'wrong; 100,000 trials, seed 1')
    q, rho = 0.7, 0.75
    bins = ((-9.0, -1.0), (-1.0, -0.605), (-0.605, -0.2), (-0.2, 9.0))
    count = {x: [0, 0, 0] for x in bins}
    rng = random.Random(1)
    for _ in range(100000):
        g = rng.gauss(0.0, 1.0)
        signals = [-1 if err else 1 for err in latent_votes(30, 1.0 - q, rho, rng, shared=g)]
        k = public_lead(signals, q)
        for lo, hi in bins:
            if lo <= g < hi:
                c = count[(lo, hi)]
                c[0] += 1
                c[1] += k < 0
                c[2] += sum(signals) <= 0
    for (lo, hi), (n, seq, blind) in count.items():
        print('  z %.3f to %.3f | %.4f | %.4f | %.4f' % (lo, hi, n / 100000, seq / n, blind / n))


def t25():
    print('T25 an item-response null for the within-difficulty estimator: data simulated with one difficulty per question '
          'and one ability per model (accuracies and the strongest fifth\'s pooled latent correlation matched), so models '
          'share nothing but difficulty; median Mantel-Haenszel odds ratio within 10 strata for the weakest, middle and '
          'strongest fifth of pairs, with all strata, without the hardest tenth and without the hardest fifth: mean and '
          'range over 20 seeds')
    for label, path in (('MMLU', DATA), ('GPQA', DATA_GPQA), ('MMLU-Pro', DATA_PRO)):
        rho = _dependence_rows(path)[-1][3]
        rec = load_counts(path)
        acc = {m: v['accuracy'] for m, v in rec['models'].items()}
        runs = [null_within_odds(acc, rec['items'], rho, seed) for seed in range(1, 21)]
        for fifth in ('weakest', 'middle', 'strongest'):
            cols = list(zip(*[r[fifth] for r in runs]))
            print('  %s | %s | all %.2f (%.2f-%.2f) | without hardest tenth %.2f (%.2f-%.2f) | without hardest fifth %.2f '
                  '(%.2f-%.2f)' % ((label, fifth) + tuple(v for c in cols for v in (math.fsum(c) / len(c), min(c), max(c)))))


def t38():
    print('T38 common-mode dilution (Proposition 6): the threshold rule of T15, adopting when the panel\'s share for the '
          'successor exceeds the share the incumbent world predicts, with agents answering the successor 0.3 of the time '
          'whatever the truth, correlated at agent rho, and people of whom 40% hold the local fact; the large-panel limit '
          'of A+ and A- and the bound on their gap, against the simulated rule with 20 agents and 5 people (T15) and with '
          '1,000 agents and 250 people: agent rho | people per agent | limit A+ A- | gap | bound | 20 and 5 | 1,000 and '
          '250; 8,000 and 2,000 trials, seed 3')
    for rho in (0.3, 0.6):
        for ratio in (0.25, 0.5):
            plus, minus = dilution_limit(0.3, rho, ratio, 0.4)
            small = [panel_run(round(20 * ratio), 20, 0.4, rho, True, 8000, 3, truth=t)['threshold'] for t in (1, 0)]
            large = [panel_run(round(1000 * ratio), 1000, 0.4, rho, True, 2000, 3, truth=t)['threshold'] for t in (1, 0)]
            print('  %.1f | %.2f | %.4f %.4f | %.4f | %.4f | %.4f %.4f | %.4f %.4f'
                  % (rho, ratio, plus, minus, plus - minus, dilution_bound(0.3, rho, ratio, 0.4), small[0], small[1],
                     large[0], large[1]))
