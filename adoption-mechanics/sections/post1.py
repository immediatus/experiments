"""Sections of Post 1, the human ledger: T1 to T10; the life of a design: T26; cross-communication: T27; review traces: T28."""
import math
import random

from actuator import band_exponent, hysteresis_band, in_hull, setter_proposal, win_set_nonempty
from career import ACCURACY_VALUE, ENDORSEMENT_WEIGHT, voice_margin
from cascades import cascade_share
from pipeline import (
    Committee,
    bikeshed,
    committee_run,
    partition_divergence,
    review_traces,
    stage_fates,
    verdict_margin,
    veto_crowding,
    window_survival,
)
from sensors import effective_n, error_floor, indicator_correlation, majority_error, variance_floor
from writeback import learn, naive_limit

TRIALS = 20000


def t1():
    print('T1 independent opinions in an equal-weight average of n members: of latent scores whose errors correlate at '
          'rho, and of right/wrong votes, whose correlation phi at an error of 0.30 is lower; n | rho | phi | effective '
          'n of scores | effective n of votes; then the ceilings 1/rho and 1/phi and the variance floor of the scores')
    for rho in (0.1, 0.25, 0.5):
        phi = indicator_correlation(0.30, rho)
        for n in (1, 3, 5, 10, 15, 30, 100):
            print('  %d | %.2f | %.4f | %.3f | %.3f' % (n, rho, phi, effective_n(n, rho), effective_n(n, phi)))
        print('  large n | %.2f | %.4f | ceiling of scores %.2f | ceiling of votes %.2f | variance floor %.3f'
              % (rho, phi, 1.0 / rho, 1.0 / phi, variance_floor(1.0, rho)))


def t2():
    print('T2 majority error of a correlated panel (one-factor model; a tie counts as wrong) against the '
          'large-panel floor Phi(Phi^-1(p)/sqrt(rho)): p | rho | floor | simulated at n = 15, 51, 201 '
          '(20,000 trials, seed 7)')
    for p, rho in ((0.30, 0.10), (0.30, 0.25), (0.20, 0.35), (0.15, 0.60), (0.10, 0.60), (0.30, 0.40)):
        sims = ' | '.join('%.4f' % majority_error(n, p, rho, TRIALS, 7) for n in (15, 51, 201))
        print('  %.2f | %.2f | %.4f | %s' % (p, rho, error_floor(p, rho), sims))


def t3():
    print('T3 runs of 30 members, true state +1, binary signals of the given precision: share of runs ending '
          'in a wrong cascade, by precision and probing weight (log-odds a member puts on revealing their '
          'signal; 0 is the classic model); closed form for probing 0 and independent signals '
          '(1-q)^2/(1-2q(1-q)); 20,000 runs, seed 1')
    for q in (0.6, 0.7, 0.8):
        row = ' | '.join('%.4f' % cascade_share(30, q, w, TRIALS, 1) for w in (0.0, 0.5, 1.0, 2.0))
        print('  %.1f | %s | closed form %.4f' % (q, row, (1 - q) ** 2 / (1 - 2 * q * (1 - q))))


def t4():
    print('T4 the career plane: voice margin (payoff of voicing a signal against the consensus minus silence) '
          'by ability self-certainty kappa and sunk endorsement of the incumbent, at horizon 0.9 and conformity '
          '0.15 (a senior) and 0.7 and 0.6 (a junior); value of accuracy %.2f, endorsement weight %.2f; dissent '
          'toward the successor, then in the incumbent\'s defence; then the endorsed senior under swept constants'
          % (ACCURACY_VALUE, ENDORSEMENT_WEIGHT))
    for toward in (True, False):
        for label, delta, gamma in (('senior', 0.9, 0.15), ('junior', 0.7, 0.6)):
            for e in (False, True):
                row = ' | '.join('%+.3f' % voice_margin(k, e, delta, gamma, toward_successor=toward)
                                 for k in (0.1, 0.3, 0.5, 0.7, 0.9))
                print('  %s | %s | endorsed %s | kappa 0.1, 0.3, 0.5, 0.7, 0.9: %s'
                      % ('toward successor' if toward else 'defending incumbent', label, 'yes' if e else 'no', row))
    for av in (0.1, 0.25, 0.5):
        for ew in (0.5, 1.0, 1.5, 2.0):
            print('  sweep | accuracy value %.2f | endorsement weight %.1f | senior endorsed, kappa 0.9: %+.3f'
                  % (av, ew, voice_margin(0.9, True, 0.9, 0.15, accuracy_value=av, endorsement_weight=ew)))


def t5():
    print('T5 veto gates of the running case (ideal points of architecture board, engineering manager, security, product): '
          'whether any change beats the status quo for every gate, by status quo position; then absorption '
          '(a fifth gate with its ideal point inside the hull), removal of one exterior gate, which gates prefer the '
          'design to the status quo inside the hull, and, from the status quo (1.0, 0.0), the compromise each gate proposes '
          'when it sets the agenda, whether it lies in the hull and which gates then veto the design; then, with the engineering manager\'s gate removed, each remaining gate\'s verdict on a revised design at (2.1, 0.28)')
    gates = list(Committee().gate_ideals)
    print('  gates | ideal points %s | design %s' % (', '.join('(%.1f, %.1f)' % g for g in gates),
                                                    '(%.1f, %.1f)' % Committee().design))
    for sq in ((0.0, 0.0), (1.0, 0.0), (1.5, 0.0), (2.0, 0.2), (2.2, 0.3), (3.5, 0.0)):
        print('  status quo %s | win-set %s' % (sq, 'nonempty' if win_set_nonempty(sq, gates) else 'empty'))
    inner = gates + [(2.05, 0.15)]
    for sq in ((0.0, 0.0), (2.0, 0.2)):
        print('  absorption | status quo %s | 4 gates %s | 5 gates %s'
              % (sq, win_set_nonempty(sq, gates), win_set_nonempty(sq, inner)))
    for i, z in enumerate(gates):
        rest = gates[:i] + gates[i + 1:]
        print('  remove gate at %s | status quo (2.0, 0.2) | win-set %s'
              % (z, 'nonempty' if win_set_nonempty((2.0, 0.2), rest) else 'empty'))
    design, sq = Committee().design, (2.0, 0.2)
    for z in gates:
        closer = (design[0] - z[0]) ** 2 + (design[1] - z[1]) ** 2 < (sq[0] - z[0]) ** 2 + (sq[1] - z[1]) ** 2
        print('  gate at %s | status quo (2.0, 0.2) | %s the design' % (z, 'prefers' if closer else 'vetoes'))
    names = ('architecture', 'engineering manager', 'security', 'product')
    for k, name in enumerate(names):
        x = setter_proposal((1.0, 0.0), gates, k)
        vetoes = [nm for nm, z in zip(names, gates)
                  if not (design[0] - z[0]) ** 2 + (design[1] - z[1]) ** 2 < (x[0] - z[0]) ** 2 + (x[1] - z[1]) ** 2]
        print('  compromise | status quo (1.0, 0.0) | %s sets the agenda | proposes (%.4f, %.4f) | in the hull %s | '
              'win-set after %s | gates then vetoing the design %s'
              % (name, x[0], x[1], 'yes' if in_hull(x, gates, eps=1e-7) else 'no',
                 'nonempty' if win_set_nonempty(x, gates) and not in_hull(x, gates, eps=1e-7) else 'empty',
                 ', '.join(vetoes) or 'none'))
    revised, rest = (2.1, 0.28), [z for z in gates if z != (1.5, -0.5)]
    for z in rest:
        closer = (revised[0] - z[0]) ** 2 + (revised[1] - z[1]) ** 2 < (sq[0] - z[0]) ** 2 + (sq[1] - z[1]) ** 2
        print('  revised design (2.1, 0.28) | engineering manager gate removed | status quo (2.0, 0.2) | gate at %s %s it'
              % (z, 'prefers' if closer else 'vetoes'))


def t6():
    print('T6 hysteresis band: abandon and adopt thresholds of the merit advantage (units of one review '
          "period's step), by sunk switching cost, at two review cadences (step deviation 1.0 with discount 0.95 "
          'per step, and step 0.5 with the discount per unit time unchanged, 0.95^0.25) and loss aversion 1 and '
          '2.25, loss weighting the periods the successor trails; then the fitted exponent of band width against cost; '
          'then the adoption threshold against the flow that repays the cost at once (option value against the '
          'Marshallian trigger); then the adopt threshold at cost 0.2 against the step size of the walk; then loss '
          'aversion applied instead to the cost of leaving the status quo')
    for sigma, disc in ((1.0, 0.95), (0.5, 0.95 ** 0.25)):
        for la in (1.0, 2.25):
            for c in (0.0125, 0.05, 0.2, 0.8):
                lo, hi = hysteresis_band(c, la, sigma, disc, tol=1e-7)
                print('  step %.1f | discount %.4f | loss aversion %.2f | cost %.4f | %.4f | %.4f | width %.4f'
                      % (sigma, disc, la, c, lo, hi, hi - lo))
        print('  exponent | step %.1f | %.3f' % (sigma, band_exponent([0.0125, 0.025, 0.05, 0.1], loss_aversion=1.0,
                                                                     sigma=sigma, discount=disc, tol=1e-7)))
    for c in (0.05, 0.2, 0.8):
        lo, hi = hysteresis_band(c, 1.0, 1.0, 0.95, tol=1e-7)
        print('  marshallian | step 1.0 | cost %.4f | flow that repays the cost at once (1 - discount) * cost %.4f | adopt '
              'threshold %.4f | ratio %.1f' % (c, (1 - 0.95) * c, hi, hi / ((1 - 0.95) * c)))
    for sigma in (0.8, 1.0, 1.25, 0.3, 0.1, 0.03):
        lo, hi = hysteresis_band(0.2, 1.0, sigma, 0.95, tol=1e-7)
        print('  step size | step %.2f | cost 0.2000 | adopt threshold %.4f | ratio to the Marshallian trigger %.1f | '
              'exponent over costs 0.1, 0.2, 0.4 %.3f'
              % (sigma, hi, hi / ((1 - 0.95) * 0.2),
                 band_exponent([0.1, 0.2, 0.4], loss_aversion=1.0, sigma=sigma, discount=0.95, tol=1e-7)))
    for c in (0.0125, 0.05, 0.2, 0.8):
        lo, hi = hysteresis_band(c, 2.25, 1.0, 0.95, tol=1e-7, loss_on='switch')
        print('  loss on the switch | step 1.0 | loss aversion 2.25 | cost %.4f | %.4f | %.4f | width %.4f'
              % (c, lo, hi, hi - lo))


def t7():
    print('T7 write-back: belief about a true driver of +1 after 2,000 recorded reasons with faithfulness phi '
          'and stories biased toward the incumbent (-0.8), noise 0.3, seed 5: naive learning (reasons taken as '
          'causes) | its limit phi*1+(1-phi)*(-0.8) | calibrated learning (the bias known and removed)')
    for phi in (0.2, 0.26, 0.3, 0.39, 0.5, 0.74, 1.0):
        print('  %.2f | %+.4f | %+.4f | %+.4f' % (phi, learn(2000, phi, 1.0, -0.8, 0.3, True, 5),
                                                   naive_limit(phi, 1.0, -0.8),
                                                   learn(2000, phi, 1.0, -0.8, 0.3, False, 5)))


def t8():
    print('T8 composition: adoption of the running case with the champion speaking first or silent, with '
          'sequential voting (cascades) or a blind simultaneous poll, by signal precision and correlation: '
          'precision | rho | silence cost without cascades | silence cost with cascades | interaction; '
          '20,000 trials, seed 1')
    for q in (0.6, 0.7, 0.8):
        for r in (0.0, 0.25, 0.5):
            def f(s, c, q=q, r=r):
                return committee_run(Committee(precision=q, rho=r, first_speaker_silent=s, cascades=c), TRIALS, 1)
            a = f(False, False) - f(True, False)
            b = f(False, True) - f(True, True)
            print('  %.1f | %.2f | %+.4f | %+.4f | %+.4f' % (q, r, a, b, b - a))


LEVERS = (
    ('baseline: champion silent, sequential vote, 3 layers, 4 gates, switching cost 0.2', {}),
    ('reversible pilot: switching cost 0.02', {'c_switch': 0.02}),
    ('one exterior gate removed', {'gate_ideals': ((2.0, 0.5), (1.5, -0.5), (2.5, -0.2))}),
    ('blind simultaneous poll', {'cascades': False}),
    ('champion insured: speaks first', {'first_speaker_silent': False}),
    ('decorrelated panel: rho 0.10', {'rho': 0.10}),
    ('flatter chain: 2 layers', {'layers': 2}),
)


def t9():
    print('T9 the running case, one lever per step in actuator-first order (each step keeps the earlier '
          'ones): step | adoption of a better design | adoption of a worse design | gap; then the same levers '
          "with the status quo inside the gates' hull (2.0, 0.2); 20,000 trials, seed 1")
    kw = {'first_speaker_silent': True}
    for name, change in LEVERS:
        kw.update(change)
        good = committee_run(Committee(**kw), TRIALS, 1)
        bad = committee_run(Committee(design_better=False, **kw), TRIALS, 1)
        print('  %s | %.4f | %.4f | %.4f' % (name, good, bad, good - bad))
    print('  monte carlo | standard error of each share at most %.4f' % (0.25 / TRIALS) ** 0.5)
    kw = {'first_speaker_silent': True, 'status_quo': (2.0, 0.2)}
    for name, change in LEVERS:
        kw.update(change)
        print('  status quo in hull | %s | %.4f' % (name, committee_run(Committee(**kw), TRIALS, 1)))


def t10():
    print('T10 sensitivity of the running case baseline (champion silent) to its constants, one at a time: '
          'constant | value | adoption of a better design | of a worse design; and divergence of groups holding '
          'separate state (15 members, rho 0.25, error 0.3): groups | share of trials with different verdicts, with '
          'the correlation shared across groups and with 0.12 of it local to each group; then the tally the gates '
          'read, a sequence against a blind poll: mean net share of endorsements; 20,000 trials')
    for field_name, values in (('gate_noise', (0.15, 0.3, 0.5)), ('merit_scale', (1.0, 1.5, 2.0)),
                               ('candor', (0.75, 0.85, 0.95)), ('loss_aversion', (1.0, 2.25, 3.0)),
                               ('precision', (0.6, 0.7, 0.8)), ('rho', (0.0, 0.25, 0.5))):
        for v in values:
            good = committee_run(Committee(first_speaker_silent=True, **{field_name: v}), TRIALS, 1)
            bad = committee_run(Committee(first_speaker_silent=True, design_better=False, **{field_name: v}), TRIALS, 1)
            print('  %s | %s | %.4f | %.4f' % (field_name, v, good, bad))
    for g in (1, 2, 3, 5):
        print('  partitions | %d | %.4f' % (g, partition_divergence(g, 15, 0.25, TRIALS, 2)))
    for g in (2, 3, 5):
        print('  partitions, 0.12 of the 0.25 local to each group | %d | %.4f'
              % (g, partition_divergence(g, 15, 0.25, TRIALS, 2, local=0.12)))
    for cascades in (True, False):
        for better in (True, False):
            c = Committee(first_speaker_silent=True, cascades=cascades, design_better=better)
            rng = random.Random(1)
            tally = math.fsum(verdict_margin(c, rng) for _ in range(TRIALS)) / TRIALS
            print('  tally | %s | %s design | mean net endorsement share %.4f'
                  % ('sequence' if cascades else 'blind poll', 'better' if better else 'worse', tally))


GROUPS = ((5, 0.8), (5, 0.65), (5, 0.65))   # the pilot team holds the most evidence; platform and product less
ROOM_SHARE = 0.12                            # of the 0.25 latent correlation, the part local to each group's room
LIFE = (
    ('groups decide apart', {}, True),
    ('the groups meet in one room', {}, False),
    ('one room, the champion speaks first', {'first_speaker_silent': False}, False),
    ('one room, the champion speaks first, the status quo among the approvers\' priorities',
     {'first_speaker_silent': False, 'status_quo': (2.0, 0.2)}, False),
)


def t26():
    print('T26 the life of a design: where reviews of a better and a worse design end, in the team review (its verdict '
          'does not favor the design), the managers\' hand-off (the unweakened verdict would have cleared every approver, '
          'the relayed one does not), at the approvals, or adopted; groups deciding apart are a pilot team of 5 at '
          'precision 0.8 and two groups of 5 at 0.65, with 0.12 of the 0.25 correlation local to each group, and stop the '
          'design when any group does not favor it; then the same groups with the evidence split three ways at the same mean '
          'precision; 20,000 reviews, seed 1')
    for name, change, apart in LIFE:
        for better in (True, False):
            c = Committee(design_better=better, **dict({'first_speaker_silent': True}, **change))
            f = stage_fates(c, TRIALS, 1, groups=GROUPS if apart else None, local=ROOM_SHARE if apart else 0.0)
            print('  %s | %s design | dies in review %.4f | dies in hand-off %.4f | dies at approvals %.4f | adopted %.4f'
                  % (name, 'better' if better else 'worse', f['review'], f['handoff'], f['approvals'], f['adopted']))
    for shares in (((5, 0.7), (5, 0.7), (5, 0.7)), GROUPS, ((5, 0.9), (5, 0.6), (5, 0.6))):
        for better in (True, False):
            f = stage_fates(Committee(design_better=better, first_speaker_silent=True), TRIALS, 1, groups=shares, local=ROOM_SHARE)
            print('  groups decide apart, evidence %s | %s design | dies in review %.4f | adopted %.4f'
                  % (' / '.join('%.2f' % q for _, q in shares), 'better' if better else 'worse', f['review'], f['adopted']))


def t27():
    print('T27 death by cross-communication, three ways: the chance a review consulting g groups decides within a '
          '13-week window when one owner settles the g(g - 1)/2 pairwise disagreements one at a time, each taking an '
          'exponential time of the given mean; where reviews of a better and a worse design end when each of the three '
          'groups of T26 votes after hearing the earlier groups\' conclusions, carried as a lead of the given number of '
          'signals per conclusion; and, with extra groups holding a veto whose ideal points lie between the status quo '
          'and the approvers\' centroid with the given scatter, the share of draws in which the status quo is in the '
          'approvers\' hull and in which every approver prefers the design; and the law of triviality: a design of 15 '
          'reviewers split into 1, 2, 4 or 8 pieces, each reviewer holding an opinion on a piece with chance '
          '0.2 times pieces to the given steepness (0: no more opinions on simpler pieces), every pair of holders '
          'settling a disagreement in a quarter of a week on average, one at a time, and each holder accepting with '
          'chance 0.9: the chance of deciding within 13 weeks, of every holder accepting, and of both; 20,000 reviews '
          'and 4,000 draws, seed 1')
    for mean in (0.5, 1.0, 2.0):
        print('  window | mean settling %.1f weeks | groups 1 to 8 | %s'
              % (mean, ' '.join('%.4f' % window_survival(g, 13.0, mean) for g in range(1, 9))))
    for carry in (0.0, 1.0, 2.0):
        for better in (True, False):
            f = stage_fates(Committee(design_better=better, first_speaker_silent=True), TRIALS, 1, groups=GROUPS,
                            local=ROOM_SHARE, carry=carry)
            print('  influence | carry %.0f | %s design | dies in review %.4f | adopted %.4f'
                  % (carry, 'better' if better else 'worse', f['review'], f['adopted']))
    for spread in (0.25, 0.5, 1.0):
        for extra in (0, 1, 2, 4, 6):
            inside, passes = veto_crowding(extra, 4000, 1, spread=spread)
            print('  vetoes | scatter %.2f | extra groups %d | status quo in hull %.4f | design passes every approver %.4f'
                  % (spread, extra, inside, passes))
    for steepness in (0.0, 0.5, 0.75, 1.0):
        for pieces in (1, 2, 4, 8):
            decides, accepted, both = bikeshed(pieces, 4000, 1, steepness=steepness)
            print('  triviality | steepness %.2f | pieces %d | decides in time %.4f | every holder accepts %.4f | both %.4f'
                  % (steepness, pieces, decides, accepted, both))


def t28():
    print('T28 review traces: the first 100 reviews of each setting of T26 (the same seed and order, so the first 100 of '
          'its 20,000), for a better and a worse design; per review, each group\'s actions and signals in speaking order '
          '(+ favors, - opposes; groups separated by /), the index where each group locked into a cascade (- if never), '
          'the net share of endorsements, the verdict as relayed through each hand-off (first unweakened), each '
          'approver\'s noise (architecture board, engineering manager, security, product), the approvers who prefer the '
          'status quo to the design, and the fate')
    for name, change, apart in LIFE:
        c0 = Committee(**dict({'first_speaker_silent': True}, **change))
        print('  setting | %s | champion %s | adoption threshold %.4f'
              % (name, 'silent' if c0.first_speaker_silent else 'speaks first',
                 review_traces(c0, 1, 1)[0]['threshold']))
        for better in (True, False):
            c = Committee(design_better=better, **dict({'first_speaker_silent': True}, **change))
            traces = review_traces(c, 100, 1, groups=GROUPS if apart else None, local=ROOM_SHARE if apart else 0.0)
            for i, t in enumerate(traces):
                acts = '/'.join(''.join('+' if a > 0 else '-' for a in g['acts']) for g in t['groups'])
                signals = '/'.join(''.join('+' if a > 0 else '-' for a in g['signals']) for g in t['groups'])
                locks = ' '.join('-' if g['lock'] is None else str(g['lock']) for g in t['groups'])
                print('  trace | %s | %s | %d | acts %s | signals %s | locks %s | margin %.4f | relayed %s | noise %s | '
                      'vetoes %s | %s' % (name, 'better' if better else 'worse', i + 1, acts, signals, locks, t['margin'],
                                         ' '.join('%.3f' % v for v in t['relayed']), ' '.join('%.3f' % v for v in t['noise']),
                                         ' '.join(str(v) for v in t['vetoes']) or '-', t['fate']))

