"""Sections of Post 3, AI as an instrument for human review: reading a long design (T29), mediation for agreement and
for difference (T30), a two-sided debate against a single advocate (T31), positional recall calibrated to published
measurements (T32), the critic and tuning (T33), the region of instrument combinations (T34), instruments that share
a source (T35), roles of one model stacked against the floor, with and without an evidence channel (T36), and the
exact majority error of a correlated panel, which sets the upper edge of the capture band (T37)."""
import itertools
import json
import os
import random

from instruments import document_use, fact_detection, fit_recall, position_recall
from pipeline import Committee, SharedInput, bikeshed, committee_run, frontier, shared_lead, stage_fates, window_survival
from sensors import error_floor, exact_majority_error, indicator_correlation

from sections.post1 import GROUPS, ROOM_SHARE

TRIALS = 20000
OVERLAP = 0.25                               # each part of a document covers (1 + overlap) / parts of it


def t29():
    print('T29 a model reading a design document: the chance it uses the decisive fact, by how much of its effective '
          'window the document fills and by how many overlapping parts it is read in (each part read in its own call, '
          'each covering 1.25 / parts of the document); a local fact sits at one uniform position, a relational fact at '
          'two that must be read together; recall by position r(x, f) = base - depth f (1 - P exp(-x/0.1) - '
          'exp(-(1 - x)/0.1)), base 0.9, primacy P fading from half the window to the window; depth swept; 20,000 '
          'documents, seed 1')
    for depth in (0.2, 0.3, 0.4):
        for relational in (False, True):
            for fill in (0.25, 0.5, 1.0):
                row = ' | '.join('%.4f' % fact_detection(fill, k, OVERLAP, relational, TRIALS, 1, depth=depth)
                                 for k in (1, 2, 4, 8))
                print('  depth %.1f | %s fact | fills %.2f of the window | parts 1, 2, 4, 8 | %s'
                      % (depth, 'relational' if relational else 'local', fill, row))


def t30():
    print('T30 mediation for agreement and for difference, in the review of T26 (three groups deciding apart, 0.12 of the '
          '0.25 correlation local to each room, champion silent): where reviews of a better and a worse design end when '
          'the groups decide apart, when an agreement mediator carries each group\'s conclusion to the next as a lead of '
          '1 or 2 signals, and when a difference mediator has every member vote blind and pools the evidence, each '
          'member counted once or by the log-odds of their group\'s precision; for the evidence split evenly, and for the '
          'best-informed group (0.8 or 0.9 against 0.65 or 0.6, the same mean precision) speaking first, second or last; then the decision window of T27 and the law of triviality when the mediator shortens '
          'each pairwise settling; 20,000 reviews and 4,000 draws, seed 1')
    modes = (('decide apart', {}), ('agreement, carry 1', {'carry': 1.0}), ('agreement, carry 2', {'carry': 2.0}),
             ('difference, pooled equally', {'pool': 'equal'}), ('difference, pooled by reliability', {'pool': 'reliability'}))
    splits = (((5, 0.7), (5, 0.7), (5, 0.7)),
              GROUPS, ((5, 0.65), (5, 0.8), (5, 0.65)), ((5, 0.65), (5, 0.65), (5, 0.8)),
              ((5, 0.9), (5, 0.6), (5, 0.6)), ((5, 0.6), (5, 0.9), (5, 0.6)), ((5, 0.6), (5, 0.6), (5, 0.9)))
    for shares in splits:
        evidence = ' / '.join('%.2f' % q for _, q in shares)
        for name, kw in modes:
            for better in (True, False):
                f = stage_fates(Committee(design_better=better, first_speaker_silent=True), TRIALS, 1, groups=shares,
                                local=ROOM_SHARE, **kw)
                print('  evidence %s | %s | %s design | dies in review %.4f | dies in hand-off %.4f | dies at approvals '
                      '%.4f | adopted %.4f' % (evidence, name, 'better' if better else 'worse', f['review'], f['handoff'],
                                               f['approvals'], f['adopted']))
    for mean in (1.0, 0.5, 0.25):
        print('  window | mean settling %.2f weeks | groups 3 to 8 | %s'
              % (mean, ' '.join('%.4f' % window_survival(g, 13.0, mean) for g in range(3, 9))))
    for mean in (0.25, 0.125, 0.0625):
        print('  triviality | mean settling %.4f weeks | pieces 1, 2, 4, 8 | decides and accepted %s'
              % (mean, ' '.join('%.4f' % bikeshed(p, 4000, 1, mean_settle=mean)[2] for p in (1, 2, 4, 8))))


def t31():
    print('T31 a two-sided debate against a single advocate, in the one-room running case with the champion silent: '
          'adoption of a better and a worse design when the members vote in order or blind, with no advocate, with the '
          'champion first, with a single advocate whose public lead toward the design is 1 or 2 signals whatever its '
          'merit, and with a debate of accuracy 0.6, 0.75 or 0.9 heard before the vote (its verdict a public lead of its '
          'log-odds, in signals) or after it (added to the tally with that weight); 20,000 reviews, seed 1')
    settings = (('no advocate', {}), ('champion first', {'first_speaker_silent': False}),
                ('single advocate, lead 1', {'advocate_lead': 1.0}), ('single advocate, lead 2', {'advocate_lead': 2.0}))
    settings += tuple(('debate %.2f heard %s' % (q, 'after' if after else 'before'), {'debate': q, 'debate_after': after})
                      for q in (0.6, 0.75, 0.9) for after in (False, True))
    for cascades in (True, False):
        for name, kw in settings:
            change = dict({'first_speaker_silent': True, 'cascades': cascades}, **kw)
            better = committee_run(Committee(**change), TRIALS, 1)
            worse = committee_run(Committee(design_better=False, **change), TRIALS, 1)
            print('  %s | %s | better adopted %.4f | worse adopted %.4f | gap %.4f'
                  % ('in order' if cascades else 'blind', name, better, worse, better - worse))


DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'liu2024_positions.json')


def t32():
    print('T32 positional recall calibrated to published measurements (Liu and coauthors 2024, multi-document question '
          'answering, 10, 20 and 30 documents): for each model, the use of the document holding the answer, (accuracy - '
          'closed book) / (oracle - closed book) clipped to [0, 1], at each printed position; the least-squares fit of '
          'Definition 5 with free weights for the beginning and the end (base, depth and the two weights are not '
          'separately identified; the fitted curve is), its use at the start, middle and end, and its root-mean-square '
          'error; then, for the fits to 20 and 30 documents, the chance a local and a relational fact are used when the '
          'document is read whole and in 4 and 8 overlapping parts, each part read at its share of the fill; '
          '20,000 documents, seed 1')
    with open(DATA, encoding='utf-8') as f:
        data = json.load(f)
    for n, block in data['documents'].items():
        xs = [(pos - 0.5) / int(n) for pos in block['positions']]
        for model, acc in block['accuracy'].items():
            closed, oracle = data['baselines'][model]
            ys = [document_use(a, closed, oracle) for a in acc]
            base, depth, primacy, recency, rms = fit_recall(xs, ys)
            shape = dict(base=base, depth=depth, primacy=primacy, recency=recency)
            ends = ' '.join('%.4f' % position_recall(x, 1.0, **shape) for x in (0.0, 0.5, 1.0))
            print('  %s documents | %s | use %s | fit start, middle, end %s | rms %.4f'
                  % (n, model, ' '.join('%.4f' % y for y in ys), ends, rms))
            if n != '10':
                for relational in (False, True):
                    row = ' | '.join('%.4f' % fact_detection(1.0, k, OVERLAP, relational, TRIALS, 1, **shape) for k in (1, 4, 8))
                    print('  reading | %s documents | %s | %s fact | whole, 4 parts, 8 parts | %s'
                          % (n, model, 'relational' if relational else 'local', row))


CRITIC_CATCH, CRITIC_FALSE = 0.85, 0.3   # a critic flags a worse design's flaw 85% of the time and a better design falsely 30%


def _critic(check, after=False, source=''):
    """A critic whose false flags people verify away with probability `check`: it says against the design with
    probability CRITIC_FALSE (1 - check) on a better design and CRITIC_CATCH on a worse one."""
    return SharedInput(1.0 - CRITIC_FALSE * (1.0 - check), 1.0 - CRITIC_CATCH, after=after, source=source)


def t33():
    print('T33 the critic and tuning, in the one-room running case with the champion silent, voting in order: adoption of '
          'a better and a worse design with no critic; a contrarian critic arguing against every design with a lead of 1 '
          'or 2 signals; a critic that flags a worse design 0.85 of the time and a better one falsely 0.3 of the time, with '
          'people verifying a share 0, 0.5 or 0.9 of the false flags away, heard before or after the vote; and members '
          'tuned to stop agreeing, putting a probing weight of 0.5, 1 or 2 log-odds on their own signal; 20,000 reviews, seed 1')
    settings = [('no critic', {}), ('contrarian critic, lead 1', {'inputs': (SharedInput(0.0, 0.0, weight=1.0),)}),
                ('contrarian critic, lead 2', {'inputs': (SharedInput(0.0, 0.0, weight=2.0),)})]
    settings += [('critic, %.1f of false flags verified away, heard %s' % (check, 'after' if after else 'before'),
                  {'inputs': (_critic(check, after),)}) for check in (0.0, 0.5, 0.9) for after in (False, True)]
    settings += [('members tuned to stop agreeing, probing weight %.1f' % w, {'probe_for': w, 'probe_against': w})
                 for w in (0.5, 1.0, 2.0)]
    for name, kw in settings:
        better = committee_run(Committee(first_speaker_silent=True, **kw), TRIALS, 1)
        worse = committee_run(Committee(first_speaker_silent=True, design_better=False, **kw), TRIALS, 1)
        print('  %s | better adopted %.4f | worse adopted %.4f | gap %.4f' % (name, better, worse, better - worse))


def _region(groups, report, debate, check, trials):
    """Every combination of reading (none, whole, four parts), combining (apart, agreement, pooled by reliability),
    debate (none, heard first, heard after) and critic (none, contrarian, verified), as (name, A+, A-) rows."""
    whole = fact_detection(1.0, 1, OVERLAP, False, TRIALS, 1)
    parts = fact_detection(1.0, 4, OVERLAP, False, TRIALS, 1)
    reading = (('no reading', ()), ('whole reading', (SharedInput(report, 1.0 - report, present=whole),)),
               ('reading in parts', (SharedInput(report, 1.0 - report, present=parts),)))
    combining = (('groups apart', {}), ('agreement mediator', {'carry': 2.0}), ('pooled by reliability', {'pool': 'reliability'}))
    debates = (('no debate', ()), ('debate first', (SharedInput(debate, 1.0 - debate),)),
               ('debate after', (SharedInput(debate, 1.0 - debate, after=True),)))
    critics = (('no critic', ()), ('contrarian critic', (SharedInput(0.0, 0.0, weight=1.0),)), ('verified critic', (_critic(check),)))
    out = []
    for (r, ri), (m, mk), (d, di), (k, ki) in itertools.product(reading, combining, debates, critics):
        inputs = ri + di + ki
        rates = [stage_fates(Committee(design_better=b, first_speaker_silent=True, inputs=inputs), trials, 1, groups=groups,
                             local=ROOM_SHARE, **mk)['adopted'] for b in (True, False)]
        out.append((' + '.join((r, m, d, k)), rates[0], rates[1]))
    return out


def t34():
    print('T34 the region of instruments: every combination of reading (none; a model reading the design whole, or in 4 '
          'overlapping parts, reporting the decisive local fact when it uses it, the report right with the given accuracy), '
          'combining (groups apart; an agreement mediator carrying conclusions as 2 signals; blind judgments pooled by '
          'reliability), debate (none, heard first, heard after) and critic (none; contrarian with a lead of 1; verified, '
          'flagging 0.85 and 0.3 with the given share of false flags verified away), in the review of T26 with the pilot '
          'team first or last; adoption of a better and a worse design, the frontier, and the widest gaps; first the '
          'running constants (report 0.95, debate 0.75, verification 0.9), then each changed alone; 20,000 reviews, seed 1')
    cases = (('pilot team first', GROUPS, 0.95, 0.75, 0.9), ('pilot team last', ((5, 0.65), (5, 0.65), (5, 0.8)), 0.95, 0.75, 0.9),
             ('pilot team first, report 0.75', GROUPS, 0.75, 0.75, 0.9),
             ('pilot team first, debate 0.9', GROUPS, 0.95, 0.9, 0.9),
             ('pilot team first, verification 0.5', GROUPS, 0.95, 0.75, 0.5))
    for label, groups, report, debate, check in cases:
        rows = _region(groups, report, debate, check, TRIALS)
        front = set(frontier([(a, b) for _, a, b in rows]))
        if label == 'pilot team first':
            for i, (name, a, b) in enumerate(rows):
                print('  region | %s | %s | better %.4f | worse %.4f | %s' % (label, name, a, b, 'frontier' if i in front else '-'))
        best = sorted(range(len(rows)), key=lambda i: rows[i][2] - rows[i][1])[:3]
        print('  summary | %s | frontier points %d | with a verified critic %d | with reading in parts %d | widest gaps %s'
              % (label, len(front), sum('verified critic' in rows[i][0] for i in front),
                 sum('reading in parts' in rows[i][0] for i in front),
                 '; '.join('%s %.4f / %.4f' % (rows[i][0], rows[i][1], rows[i][2]) for i in best)))


def _instruments(sources):
    """The leading instruments of T34, each model-made input labelled with the source given for it: the reader (report
    0.95, used with T29's chance for four parts at a full window), the debate (0.75, heard first) and the critic,
    unverified or with 0.9 of its false flags verified away by people."""
    parts = fact_detection(1.0, 4, OVERLAP, False, TRIALS, 1)
    reader = SharedInput(0.95, 0.05, present=parts, source=sources[0])
    debate = SharedInput(0.75, 0.25, source=sources[1])
    return {'debate first': (debate,), 'critic, unverified': (_critic(0.0, source=sources[2]),),
            'critic, verified': (_critic(0.9, source=sources[2]),),
            'reading in parts + debate first + critic, unverified': (reader, debate, _critic(0.0, source=sources[2])),
            'reading in parts + debate first + critic, verified': (reader, debate, _critic(0.9, source=sources[2]))}


def t35():
    print('T35 instruments that share a source: the leading instruments of T34 in the review of T26 (pilot team first, groups '
          'deciding apart or pooled by reliability), when every model-made instrument errs independently, when each comes '
          'from a different model family whose errors correlate at the given latent cross-family value, and when all come '
          'from one family prompted into different roles, correlating at the given latent within-family value; the critic\'s '
          'verification is done by people and stays independent; members add every instrument\'s log-odds as if '
          'independent; then the right-or-wrong correlation each latent value implies at an error of 0.25, for comparison '
          'with measured judge correlations; 20,000 reviews, seed 1')
    conditions = [('independent instruments', ('', '', ''), 0.0, 0.0)]
    conditions += [('separate families, cross %.1f' % r, ('reader', 'debate', 'critic'), r, r) for r in (0.3, 0.6)]
    conditions += [('one family in three roles, within %.1f' % r, ('model', 'model', 'model'), r, 0.0) for r in (0.3, 0.6, 0.9)]
    for label, sources, family, cross in conditions:
        for name, inputs in _instruments(sources).items():
            for rule, kw in (('groups apart', {}), ('pooled by reliability', {'pool': 'reliability'})):
                rates = [stage_fates(Committee(design_better=b, first_speaker_silent=True, inputs=inputs, family_rho=family,
                                               cross_rho=cross), TRIALS, 1, groups=GROUPS, local=ROOM_SHARE, **kw)['adopted']
                         for b in (True, False)]
                print('  %s | %s | %s | better %.4f | worse %.4f | gap %.4f' % (label, name, rule, rates[0], rates[1], rates[0] - rates[1]))
    for r in (0.3, 0.6, 0.9):
        print('  latent %.1f | right-or-wrong correlation at an error of 0.25 | %.4f' % (r, indicator_correlation(0.25, r)))


def t36():
    print('T36 roles of one model stacked against the floor: k inputs from one source, each right 0.75 of the time, heard '
          'first by every member and added as if independent; the share of reviews in which their combined verdict is '
          'wrong, for k = 1, 3, 9, 21 and 41 roles and a latent within-source correlation of 0, 0.3, 0.6 and 0.9, against '
          'the floor of Proposition 1 at an error of 0.25; then the blind one-room review hearing the stack first; then a '
          'debate heard first that is a fourth role of the same source (0.75) against one with an evidence channel the '
          'panel lacks (0.9, independent), alongside a reader and an unverified critic from the source; 20,000 reviews, seed 1')
    for rho in (0.0, 0.3, 0.6, 0.9):
        row = []
        for k in (1, 3, 9, 21, 41):
            c = Committee(inputs=tuple(SharedInput(0.75, 0.25, source='model') for _ in range(k)), family_rho=rho)
            rng, wrong = random.Random(1), 0
            for _ in range(TRIALS):
                lead, _ = shared_lead(c, 1, rng)
                wrong += lead <= 0
            row.append(wrong / TRIALS)
        floor = error_floor(0.25, rho) if rho > 0 else 0.0
        print('  stack | within %.1f | wrong for 1, 3, 9, 21, 41 roles | %s | floor %.4f'
              % (rho, ' '.join('%.4f' % v for v in row), floor))
    for rho in (0.3, 0.6, 0.9):
        for k in (1, 9, 41):
            inputs = tuple(SharedInput(0.75, 0.25, source='model') for _ in range(k))
            rates = [committee_run(Committee(design_better=b, first_speaker_silent=True, cascades=False, inputs=inputs,
                                             family_rho=rho), TRIALS, 1) for b in (True, False)]
            print('  review | within %.1f | %d roles heard first | better %.4f | worse %.4f' % (rho, k, rates[0], rates[1]))
    parts = fact_detection(1.0, 4, OVERLAP, False, TRIALS, 1)
    for rho in (0.3, 0.6, 0.9):
        base = (SharedInput(0.95, 0.05, present=parts, source='model'), _critic(0.0, source='model'))
        for name, debate in (('debate as a fourth role', SharedInput(0.75, 0.25, source='model')),
                             ('debate with an evidence channel', SharedInput(0.9, 0.1))):
            rates = [stage_fates(Committee(design_better=b, first_speaker_silent=True, inputs=base + (debate,), family_rho=rho),
                                 TRIALS, 1, groups=GROUPS, local=ROOM_SHARE)['adopted'] for b in (True, False)]
            print('  channel | within %.1f | %s | better %.4f | worse %.4f | gap %.4f' % (rho, name, rates[0], rates[1], rates[0] - rates[1]))


def t37():
    print('T37 exact majority error of a correlated panel (one-factor model; a tie counts as wrong), by integration over '
          'the shared factor, against the simulation of T2 and the large-panel floor: p | rho | floor | exact at n = 15, '
          '51, 201')
    for p, rho in ((0.30, 0.10), (0.30, 0.25), (0.20, 0.35), (0.15, 0.60), (0.10, 0.60), (0.30, 0.40)):
        exact = ' | '.join('%.4f' % exact_majority_error(n, p, rho) for n in (15, 51, 201))
        print('  %.2f | %.2f | %.4f | %s' % (p, rho, error_floor(p, rho), exact))
    room = 1 - exact_majority_error(15, 0.30, 0.25)
    print('  capture band of the running panel, fifteen members right 0.70 of the time and correlated at 0.25, with no '
          'probing weight: from 0.7000 to %.4f' % room)
