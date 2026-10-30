"""Figure specifications for Capacity in Arrears, built from the frozen results.

Every plotted number is parsed from the results file, so a figure cannot drift from the
executed code. A specification is a plain dict (id, height, margins, axes X, Y and optional
R, and a list of elements: hband, rect, vline, hline, band, line, pt, txt). Two backends draw
it: a canvas script for the posts and an SVG file for the repository.

  figures(results_path) -> list of Figure(name, spec, aria, caption)
"""
import math
import re

from results import cells, number, read, rows
from svg import Figure

RESULTS = {}                 # the sections of the results file being drawn, set by figures()


def section(tag):
    """The rows of one section of the results being drawn."""
    return rows(RESULTS[tag])


def _series(items):
    """Items joined as prose: 'a', 'a and b', 'a, b and c'."""
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def base(fid, h, ml=(40, 50), mr=(14, 16), mt=24, mb=42):
    """An empty specification: id, height, margins (narrow, wide) and no elements yet."""
    return dict(id=fid, h=h, ml=list(ml), mr=list(mr), mt=mt, mb=mb, els=[])


FIGS = []


# ---------- Part 1 ----------

def fig_stale():
    rows = [cells(row) for row in section('T15')]
    d = [int(r[0]) for r in rows]
    exact = [number(r[1]) for r in rows]
    suff = [number(r[2]) for r in rows]
    s = base('chart-stale', 300)
    s['X'] = dict(lo=-0.2, hi=4.3, ticks=[[v, '%d' % v] for v in d], title='sync periods of staleness, d', ntitle='staleness d (syncs)')
    s['Y'] = dict(lo=0, hi=2.2, ticks=[[0, '0'], [0.5, '0.5'], [1, '1.0'], [1.5, '1.5'], [2, '2.0']], title='largest stable gain', ntitle='stable gain')
    e = s['els']
    e.append(dict(t='hline', y=1, c='a', w=2))
    e.append(dict(t='txt', x=4.3, y=1, s='the one-line rule: gain 1', n='rule: gain 1', al='right', bl='bottom', dy=-3, c='a', b=True))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(d, exact)], c='b', mk=4))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(d, suff)], c='g', dash=True, mk=3, open=True))
    for a, b in zip(d, exact):
        e.append(dict(t='txt', x=a, y=b, s='%.3f' % b, al='left', bl='bottom', dx=6, dy=-2, c='b'))
    e.append(dict(t='txt', x=0.55, y=1.62, s='exact bound, Levin and May', n='exact bound', c='b', bl='bottom'))
    e.append(dict(t='txt', x=2.0, y=0.05, s='sufficient bound 1/(1+d)', n='sufficient 1/(1+d)', c='g', bl='bottom'))
    e.append(dict(t='txt', x=1.4, y=1, s='on the edge: period 6', n='', al='left', bl='bottom', dy=-5, c='ink'))
    e.append(dict(t='txt', x=3, y=0.445, s='beyond it: diverges', n='diverges', al='center', bl='bottom', dy=-26, c='ink'))
    aria = ('Largest stable gain against staleness in sync periods. The exact bound falls from 2.000 at zero periods to 1.000 at one, '
            '0.618 at two, 0.445 at three and 0.347 at four. The sufficient bound one over one plus d lies below it. The one-line rule has gain 1, '
            'which touches the exact bound at one period and lies above it from two periods on.')
    cap = ('The largest gain at which the stale ratio rule still settles, against how many sync periods old its replica count is. '
           'The rule\'s gain of 1 meets the exact bound at one stale period, where it oscillates forever, and exceeds it from two periods on, '
           'where it diverges. The sufficient bound, Proposition 22 of Self-Healing Without Connectivity, sits well inside the exact one.')
    FIGS.append(Figure('stale', s, aria, cap))


def fig_staircase_stats():
    rows = [cells(row) for row in section('T2')]
    k = [number(r[0]) for r in rows]
    rounds = [int(r[1]) for r in rows]
    tcap = [number(r[2]) for r in rows]
    back = [number(r[4]) for r in rows]
    xt = [[v, '%dx' % v] for v in (3, 5, 10, 30, 100, 300)]
    s = base('chart-staircase-time', 280, ml=(38, 48), mr=(14, 16))
    s['X'] = dict(lo=2.5, hi=380, log=True, ticks=xt, title='overload, log scale', ntitle='overload (log)')
    s['Y'] = dict(lo=0, hi=1100, ticks=[[v, '%d s' % v] for v in (0, 250, 500, 750, 1000)], title='time until capacity meets the load', ntitle='time to capacity')
    e = s['els']
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(k, tcap)], c='b', mk=4))
    for a, b, r in zip(k, tcap, rounds):
        e.append(dict(t='txt', x=a, y=b, s='%d s, %d round%s' % (b, r, '' if r == 1 else 's'), n='%d s' % b, al='left' if a < 4 else 'right', bl='top' if a < 4 else 'bottom', dx=6 if a < 4 else -6, dy=6 if a < 4 else -6, c='b'))
    aria = ('Time until capacity meets the load against overload on a log scale: 105 s at 3x (1 round), 225 s at 5x (2), 345 s at 10x (3), '
            '480 s at 30x (4), 705 s at 100x (6) and 945 s at 300x (8). On the log scale the points lie close to a straight line.')
    cap = ('Time until capacity meets the load against the size of the overload, on a log scale. A straight line here means time grows with the logarithm '
           'of the overload: one round of about two minutes per doubling. Model: fluid queue, no timeouts or retries, every pod serves its full rate when saturated.')
    FIGS.append(Figure('staircase-time', s, aria, cap))
    s = base('chart-staircase-backlog', 280, ml=(44, 54), mr=(14, 16))
    s['X'] = dict(lo=2.5, hi=380, log=True, ticks=xt, title='overload, log scale', ntitle='overload (log)')
    s['Y'] = dict(lo=50, hi=500000, log=True, ticks=[[100, '100'], [1000, '1k'], [10000, '10k'], [100000, '100k']], title='peak backlog, seconds of the original load (log)', ntitle='peak backlog (log)')
    e = s['els']
    e.append(dict(t='line', pts=[[3, back[0]], [300, back[0] * 100]], c='g', w=1.2, dash=True))
    e.append(dict(t='txt', x=30, y=back[0] * 10, s='growth in proportion to the overload', n='proportional', al='left', bl='top', dx=4, dy=8, c='g'))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(k, back)], c='a', mk=4))
    for a, b in zip(k, back):
        lab = '{:,}'.format(int(b))
        e.append(dict(t='txt', x=a, y=b, s=lab, n=lab if a in (3, 30, 300) else '', al='left' if a < 4 else 'right', bl='top' if a < 4 else 'bottom', dx=6 if a < 4 else -6, dy=8 if a < 4 else -6, c='a'))
    aria = ('Peak backlog in seconds of the original load against overload, both on log scales: 105 at 3x, 447 at 5x, 1,836 at 10x, 10,530 at 30x, '
            '55,869 at 100x and 224,841 at 300x. A dashed line shows growth in proportion to the overload from the 3x point, reaching 10,500 at 300x; '
            'the measured backlog rises above it more steeply.')
    cap = ('Peak backlog against the size of the overload, both on log scales. The dashed line is what growth in proportion to the overload would look like. '
           'The backlog climbs more steeply than that, because every round is paid in full at the new rate. Model: as in the figure above.')
    FIGS.append(Figure('staircase-backlog', s, aria, cap))


def fig_frontier():
    rows = [cells(row) for row in section('T4')]
    pts = []
    for r in rows:
        lim = number(r[0])
        tgt = number(r[1])
        rnd = int(r[3])
        t = number(r[4])
        pts.append((lim, tgt, 100.0 / tgt, rnd, t))
    s = base('chart-frontier', 330, ml=(32, 40), mr=(14, 16))
    s['X'] = dict(lo=1.0, hi=4.3, ticks=[[v, '%g' % v] for v in (1, 1.5, 2, 2.5, 3, 3.5, 4)], title='pods held per pod of steady demand', ntitle='pods per pod of demand')
    s['Y'] = dict(lo=0, hi=16.5, ticks=[[v, '%d' % v] for v in (0, 4, 8, 12, 16)], title='rounds to meet a 30x overload', ntitle='rounds, 30x overload')
    e = s['els']
    fam = sorted([p for p in pts if p[0] == 1], key=lambda p: p[2])
    e.append(dict(t='line', pts=[[p[2], p[3]] for p in fam], c='b', mk=4))
    for p in fam:
        lab = '%d%%, %s s' % (p[1], '{:,}'.format(int(p[4])))
        far = p[2] > 3
        if abs(p[2] - 2.0) < 1e-9:
            e.append(dict(t='txt', x=p[2], y=p[3], s=lab, n='%d%%' % p[1], al='left', bl='bottom', dx=6, dy=-8, c='b'))
            continue
        e.append(dict(t='txt', x=p[2], y=p[3], s=lab, n='%d%%' % p[1], al='right' if far else 'left', bl='bottom' if far else 'middle', dx=-4 if far else 7, dy=-8 if far else 0, c='b'))
    for p in [p for p in pts if p[0] != 1]:
        e.append(dict(t='pt', x=p[2], y=p[3], c='c', r=5))
        e.append(dict(t='txt', x=p[2], y=p[3], s='50%%, limit %dx request, %d s' % (p[0], p[4]), n='limit %dx' % p[0], al='left', bl='middle', dx=8, c='c'))
    e.append(dict(t='txt', x=4.0, y=2, s='dominated', al='center', bl='top', dy=8, c='a', b=True))
    e.append(dict(t='txt', x=1.25, y=15, s='API default', n='default', al='left', bl='bottom', dx=-4, dy=-8, c='ink'))
    aria = ('Rounds to meet a thirtyfold overload against pods held per pod of steady demand. With the limit equal to the request: 25% target holds 4.00 '
            'and takes 2 rounds, 50% holds 2.00 and takes 4, 60% holds 1.67 and takes 6, 70% holds 1.43 and takes 9, 80% holds 1.25 and takes 15. '
            'At a 50% target, a limit twice the request takes 2 rounds and four times takes 1, both holding 2.00, which dominates the 25% point.')
    cap = ('The achievable region of Definition 3 for a thirtyfold overload. Blue: targets with the limit equal to the request, every one on the frontier. '
           'Green: a 50% target with the limit raised to twice and four times the request. The 25% point needs twice the steady pods of the green point at '
           'the same two rounds, so it is dominated once the limit can vary. Model: as in the staircase figure.')
    FIGS.append(Figure('frontier', s, aria, cap))


def fig_hottest():
    rows = [cells(row) for row in section('T21')]
    s = base('chart-hottest', 340, ml=(36, 44), mr=(34, 40))
    s['X'] = dict(lo=0.85, hi=18, log=True, ticks=[[v, '%d' % v] for v in (1, 2, 4, 6, 15)], title='round budget R, log scale', ntitle='round budget R (log)')
    s['Y'] = dict(lo=0, hi=100, ticks=[[v, '%d%%' % v] for v in (0, 20, 40, 60, 80, 100)], title='hottest target allowed', ntitle='hottest target')
    e = s['els']
    e.append(dict(t='hband', y0=91, y1=100, c='a', al=0.14))
    e.append(dict(t='txt', x=0.9, y=95.5, s='dead band: a saturated metric never scales', n='dead band', al='left', c='a', dx=4))
    cols = {'3x': 'c', '10x': 'b', '30x': 'e', '100x': 'd'}
    for r in rows:
        k = r[0]
        cs = []
        for cell in r[1:]:
            m = re.match(r'R=(\d+): (\d+)%, (never|\d+ s)', cell)
            R, t, res = int(m.group(1)), int(m.group(2)), m.group(3)
            cs.append((R, t, res))
        e.append(dict(t='line', pts=[[R, t] for R, t, _ in cs], c=cols[k], mk=3.5))
        e.append(dict(t='txt', x=15, y=cs[-1][1], s=k, al='left', dx=9, c=cols[k], b=True))
        for R, t, res in cs:
            sec = None if res == 'never' else int(res.split()[0])
            miss = res == 'never' or (sec is not None and sec > R * 120 + 15)
            if miss:
                e.append(dict(t='pt', x=R, y=t, c='a', r=8, open=True))
                lab = 'never scales' if res == 'never' else '%d s, a round late' % sec
                if R >= 6:
                    e.append(dict(t='txt', x=R, y=t, s='%d%%: %s' % (t, lab), n='%d%%' % t, al='right', bl='bottom', dx=-10, dy=-4, c='a'))
                elif R == 1:
                    e.append(dict(t='txt', x=R, y=t, s='%d%%: %s' % (t, lab), n='%d%%' % t, al='left', bl='top', dx=8, dy=6, c='a'))
                else:
                    e.append(dict(t='txt', x=0.95, y=84, s='circled: %s at %d%%, %s' % (k, t, lab), n='', al='left', bl='middle', c='a'))
                    e.append(dict(t='txt', x=R, y=t, s='', n='%d%%' % t, al='right', bl='bottom', dx=-10, dy=-6, c='a'))
    aria = ('Hottest target allowed by Corollary 2 against the round budget, one curve per overload. 3x: 57, 69, 80, 85 and 93% for budgets of 1, 2, 4, 6 '
            'and 15 rounds. 10x: 31, 46, 63, 71, 86%. 30x: 18, 32, 50, 61, 80%. 100x: 10, 21, 39, 51, 74%. Targets of 91% and above fall in a shaded dead band. '
            'Three simulated cells miss their budget and are circled: 3x at 93% never scales, 10x at 63% takes 585 s, 100x at 10% takes 210 s.')
    cap = ('The hottest whole-percent target Corollary 2 allows for each overload and round budget, with the limit equal to the request. Each point was '
           'then simulated at that target. Circled points missed their budget: the 93% target sits in the dead band of Corollary 1, the tolerance band ends a '
           'round early at 63%, and truncation leaves the 10% order one pod short. A round costs about 120 s in the specimen; a point counts as late only beyond R rounds plus one 15-second sync of alignment.')
    FIGS.append(Figure('hottest', s, aria, cap))


def fig_efficiency():
    rows = [cells(row) for row in section('T10')]
    xt = [[v, '%d%%' % round(v * 100)] for v in (0.4, 0.6, 0.8, 1.0)]
    for which, col, ylab, ticks, hi, fmt, fid in (
            (2, 'b', 'time until capacity meets the load', [[v, '%d s' % v] for v in (0, 200, 400, 600, 800)], 820, '%d s', 'efficiency-time'),
            (4, 'a', 'peak pods over pods needed', [[v, '%dx' % v] for v in (0, 4, 8, 12)], 14.5, '%.2fx', 'efficiency-peak')):
        s = base('chart-' + fid, 260, ml=(40, 50), mr=(14, 16))
        s['X'] = dict(lo=0.33, hi=1.07, ticks=xt, title='rate a saturated pod still serves', ntitle='saturated pod rate')
        s['Y'] = dict(lo=0, hi=hi, ticks=ticks, title=ylab, ntitle=ylab.replace('time until capacity meets the load', 'time to capacity'))
        e = s['els']
        for k, c in (('10x', 'b'), ('30x', 'd')):
            sel = [r for r in rows if r[0] == k]
            pts = [[number(r[1]), number(r[which])] for r in sel]
            e.append(dict(t='line', pts=pts, c=c, mk=4))
            e.append(dict(t='txt', x=pts[-1][0], y=pts[-1][1], s=k, al='right', bl='middle', dx=-10, c=c, b=True))
            above = k == '30x'
            for x, y in pts:
                e.append(dict(t='txt', x=x, y=y, s=fmt % y, n=(fmt % y) if x in (0.4, 1.0) else '', al='center', bl='bottom' if above else 'top', dy=-8 if above else 8, c=c))
        FIGS.append((fid, s))
    aria_t = ('Time until capacity meets the load against the rate a saturated pod still serves. Tenfold overload: 345 s at 100% and 80%, 465 s at 60% and 40%. '
              'Thirtyfold: 480 s at 100%, 585 s at 80% and 60%, 705 s at 40%.')
    aria_p = ('Peak pods over pods needed against the rate a saturated pod still serves. Tenfold: 3.17 at 100% and 80%, 6.30 at 60%, 10.08 at 40%. '
              'Thirtyfold: 4.17 at 100% and 80%, 8.27 at 60%, 13.23 at 40%.')
    cap_t = ('What degradation under load does to the time until capacity meets the load, for a tenfold and a thirtyfold overload. As saturated pods serve '
             'less of their nominal rate, capacity arrives a round or two later. Model: as in the staircase figures.')
    cap_p = ('The same runs, peak pods over pods needed. The overshoot roughly doubles at 60% and triples at 40%, because a slower drain keeps the metric '
             'saturated and the controller multiplying for longer.')
    out = []
    for f in FIGS:
        if f[0] == 'efficiency-time':
            out.append(Figure('efficiency-time', f[1], aria_t, cap_t))
        elif f[0] == 'efficiency-peak':
            out.append(Figure('efficiency-peak', f[1], aria_p, cap_p))
        else:
            out.append(f)
    FIGS[:] = out


# ---------- Part 2 ----------

def fig_phi():
    rows = [cells(row) for row in section('T11')]
    w = [number(r[0]) for r in rows]
    ph = [number(r[1]) for r in rows]
    t25 = [cells(row) for row in section('T25')]
    phi01 = number(t25[1][4]) / 100.0
    t37 = section('T37')
    longp = {float(a): float(b) for a, b in re.findall(r'(\d+): (\d+\.\d+)', [row for row in t37 if row.startswith('(b)')][0])}
    m = re.search(r'c = ([\d.]+), w0 = ([\d.]+)', [row for row in t37 if row.startswith('(c)')][0])
    cc, w0 = float(m.group(1)), float(m.group(2))
    s = base('chart-phi', 340, ml=(34, 42), mr=(14, 16))
    s['X'] = dict(lo=0.08, hi=700, log=True, ticks=[[0.1, '0.1'], [1, '1'], [3.33, '3.33'], [10, '10'], [100, '100'], [400, '400']],
                  nticks=[[0.1, '0.1'], [1, '1'], [10, '10'], [100, '100']], title='window over dead time, w = W/τ (log scale)', ntitle='w = W/τ (log)')
    s['Y'] = dict(lo=0, hi=3, ticks=[[0, '0'], [0.5, '0.5'], [1, '1.0'], [1.5, '1.5'], [2, '2.0'], [2.5, '2.5'], [3, '3.0']], title='standing delay needed, in dead times, Φ(w)', ntitle='Φ(w), dead times')
    e = s['els']
    e.append(dict(t='hline', y=math.e, c='a', w=1.5, dash=True))
    e.append(dict(t='txt', x=0.09, y=math.e, s='e: no window can demand more (Proposition 5)', n='ceiling e (Prop. 5)', bl='bottom', dy=-3, c='a'))
    e.append(dict(t='hline', y=2 / math.pi, c='g', w=1, dash=True))
    e.append(dict(t='txt', x=650, y=2 / math.pi, s='pure delay, 2/π', n='2/π', al='right', bl='top', dy=3, c='g'))
    def hb(x):
        al = math.pi / (1 + x)
        return ((1 + math.cos(al)) + (math.pi + al) * math.sin(al)) / (2 * math.pi * al)
    hbp = [[x, hb(x)] for x in [1 * (6 ** (i / 40)) for i in range(41)]]
    asy = [[x, math.e / (1 + cc / math.log(x / w0) ** 2)] for x in [2.5 * (160 ** (i / 60)) for i in range(61)]]
    e.append(dict(t='line', pts=hbp, c='c', w=2, dash=True))
    e.append(dict(t='line', pts=asy, c='d', w=2, dash=True))
    e.append(dict(t='txt', x=1.0, y=0.78, s='closed form, Prop. 5a', n='closed form', al='right', dx=-4, c='c'))
    e.append(dict(t='txt', x=650, y=2.05, s='asymptotic form', n='asymptotic', al='right', bl='bottom', c='d'))
    pts = [[0.1, phi01]] + [[a, b] for a, b in zip(w, ph)] + [[a, b] for a, b in sorted(longp.items())]
    e.append(dict(t='line', pts=pts, c='b', mk=3.5, w=1.2))
    e.append(dict(t='txt', x=0.1, y=phi01, s='%.3f' % phi01, al='left', bl='bottom', dx=4, dy=-4, c='b'))
    for a, b in sorted(longp.items()):
        e.append(dict(t='txt', x=a, y=b, s='%.3f' % b, n='%.2f' % b, al='right', bl='top', dx=-4, dy=6, c='b'))
    i3 = w.index(3.33)
    e.append(dict(t='pt', x=3.33, y=ph[i3], c='b', r=7, open=True))
    e.append(dict(t='txt', x=3.33, y=ph[i3], s='default window: %.3f' % ph[i3], n='default %.2f' % ph[i3], al='left', bl='top', dx=8, dy=6, c='b'))
    aria = ('Standing delay needed, in dead times, against the window over the dead time on a log scale. The computed curve rises from 0.119 at w = 0.1 '
            'to 0.384 at 0.5, 0.573 at 1, 0.916 at 3.33, 1.213 at 10, 1.539 at 40, %.3f at 100 and %.3f at 400. The closed-form harmonic-balance '
            'approximation follows it closely from 1 to about 3 and then rises too fast; the asymptotic form e over one plus %.1f over the squared log of w over %.2f '
            'follows it from about 3 to 400. Dashed lines mark e, the ceiling of Proposition 5, and 2 over pi for the pure-delay loop.') % (longp[100.0], longp[400.0], cc, w0)
    cap = ('Φ(w), the standing delay the idealized loop needs, against the window measured in dead times. Blue points: computed. Green dashed: the closed form of '
           'Proposition 5a, derived by harmonic balance and drawn for w from 1 to 6. Orange dashed: the asymptotic form e/(1 + c/ln²(w/w₀)), whose shape comes from '
           'the roots near e and whose two constants are fitted on w from 10 to 400. The two approximations bracket the default window from opposite sides. '
           'Model: the idealized min-max loop with no sampling, rounding, tolerance or ceilings.')
    FIGS.append(Figure('phi', s, aria, cap))


def fig_agreement():
    rows = [cells(row) for row in section('T12') if not row.startswith('mean')]
    s = base('chart-agreement', 360, ml=(40, 50), mr=(14, 16))
    s['X'] = dict(lo=15, hi=185, ticks=[[v, '%d s' % v] for v in (20, 60, 100, 140, 180)], title='predicted boundary, τ_eff Φ(W_eff/τ_eff)', ntitle='predicted boundary')
    s['Y'] = dict(lo=15, hi=185, ticks=[[v, '%d s' % v] for v in (20, 60, 100, 140, 180)], title='observed boundary in the deployed loop', ntitle='observed boundary')
    e = s['els']
    e.append(dict(t='band', pts=[[x, x / 1.1, x / 0.9] for x in (15, 185)], c='g', al=0.12))
    e.append(dict(t='line', pts=[[15, 15], [185, 185]], c='g', w=1, dash=True))
    e.append(dict(t='txt', x=160, y=160 / 0.9, s='±10%', al='right', bl='middle', dx=-6, c='g'))
    cols = {30: 'c', 60: 'b', 90: 'e', 180: 'd'}
    for dead in (30, 60, 90, 180):
        sel = [r for r in rows if int(r[0]) == dead]
        pts = [[number(r[4]), number(r[2])] for r in sel]
        for x, y in pts:
            e.append(dict(t='pt', x=x, y=y, c=cols[dead], r=4.5))
        last = pts[-1]
        far = last[0] > 150
        e.append(dict(t='txt', x=last[0], y=last[1], s='τ = %d s' % dead, al='right' if far else 'left', bl='top', dx=-6 if far else 6, dy=6, c=cols[dead], b=True))
    d90 = [r for r in rows if int(r[0]) == 90 and int(r[1]) == 300][0]
    e.append(dict(t='pt', x=number(d90[4]), y=number(d90[2]), c='e', r=8, open=True))
    e.append(dict(t='txt', x=number(d90[4]), y=number(d90[2]), s='default window: %.1f predicted, %.1f observed' % (number(d90[4]), number(d90[2])), n='default', al='right', bl='bottom', dx=-8, dy=-6, c='e'))
    worst = [r for r in rows if int(r[0]) == 30 and int(r[1]) == 120][0]
    e.append(dict(t='pt', x=number(worst[4]), y=number(worst[2]), c='c', r=8, open=True))
    e.append(dict(t='txt', x=number(worst[4]), y=number(worst[2]), s='largest miss, 14%', n='', al='left', bl='top', dx=8, dy=8, c='ink'))
    aria = ('Observed hunting boundary of the deployed loop against the prediction with ten seconds of sampling delay, for sixteen pairs of dead time and window. '
            'Points lie along the diagonal. Four fall outside the ten percent band, all with the prediction above the observation: dead time 30 s with windows '
            'of 120 and 300 s, 60 s with 300 s, and 90 s with 600 s, the last by a hair; the largest miss is 30 s and 120 s, predicted 36.4 s, observed 31.8 s. '
            'At a 90 s dead time the default 300 s window is predicted at 89.6 s and observed at 85.5 s.')
    cap = ('Each point is one pair of dead time and window; for each dead time, the windows of 60, 120, 300 and 600 seconds give the four points from left to right. '
           'Points on the dashed diagonal would be perfect predictions; the shaded band is ±10%. The prediction lands within 6% on average and 14% at worst. Every '
           'miss larger than 10% is an overestimate, three of the four at the two shortest dead times. '
           'Model: ported controller, 15-second sync, demand stepping from 50 to 200 pods needed, last hour of a 20-hour run.')
    FIGS.append(Figure('agreement', s, aria, cap))


def fig_cost():
    rows = [cells(row) for row in section('T13')]

    def rng(c):
        m = re.match(r'(\d+)\.\.(\d+) \((\d+)\)', c)
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    D = [int(r[0]) for r in rows]
    nf = [rng(r[1]) for r in rows]
    n30 = [rng(r[3]) for r in rows]
    t12 = [cells(row) for row in section('T12') if not row.startswith('mean')]
    obs = number([r for r in t12 if int(r[0]) == 90 and int(r[1]) == 300][0][2])
    s = base('chart-cost', 350, ml=(40, 50), mr=(14, 16))
    s['X'] = dict(lo=30, hi=310, ticks=[[v, '%d s' % v] for v in (40, 80, 120, 160, 200, 240, 280)], nticks=[[v, '%d' % v] for v in (40, 120, 200, 280)], title='standing delay D = T/c', ntitle='standing delay (s)')
    s['Y'] = dict(lo=0, hi=700, ticks=[[v, '%d' % v] for v in (0, 100, 200, 300, 400, 500, 600, 700)], title='pods, 5th to 95th percentile', ntitle='pods')
    e = s['els']
    e.append(dict(t='band', pts=[[d, a[0], a[1]] for d, a in zip(D, n30)], c='d', al=0.0, edge=True))
    e.append(dict(t='band', pts=[[d, a[0], a[1]] for d, a in zip(D, nf)], c='b', al=0.25))
    e.append(dict(t='hline', y=200, c='g', w=1, dash=True))
    e.append(dict(t='vline', x=obs, c='ink', dash=True))
    e.append(dict(t='txt', x=obs, y=650, s='observed boundary %.1f s' % obs, n='boundary', al='left', dx=5, c='ink'))
    e.append(dict(t='line', pts=[[d, a[2]] for d, a in zip(D, nf)], c='a', w=2, mk=3.5))
    for d, a in zip(D, nf):
        if d in (40, 60, 80):
            e.append(dict(t='txt', x=d, y=a[2], s='+%d%%' % math.floor(100.0 * (a[2] - 200) / 200 + 0.5), n='+%d%%' % math.floor(100.0 * (a[2] - 200) / 200 + 0.5), al='right' if d == 80 else 'left', bl='top' if d == 80 else 'bottom', dx=-8 if d == 80 else 8, dy=4 if d == 80 else -4, c='a'))
    e.append(dict(t='txt', x=150, y=200, s='flat at 200', n='200', al='center', bl='bottom', dy=-5, c='b'))
    e.append(dict(t='txt', x=300, y=n30[-1][1], s='30% noise', n='30% noise', al='right', bl='bottom', dy=-4, c='d'))
    i150 = D.index(150)
    e.append(dict(t='txt', x=150, y=n30[i150][1], s='%d to %d' % n30[i150][:2], n='', al='center', bl='bottom', dy=-4, c='d'))
    hunting = [(d, a) for d, a in zip(D, nf) if d < 100]
    settled = [a for d, a in zip(D, nf) if d >= 100]
    flat = _series([str(d) for d, a in zip(D, nf) if d >= 100 and a[0] == a[1] == 200])
    aria = ('Pods against standing delay at a 90 s dead time and the default window, 200 pods needed. Noise-free, the 5th to 95th percentile band is '
            + ', '.join(('%d to %d pods at %d s' if i == 0 else '%d to %d at %d s') % (a[0], a[1], d) for i, (d, a) in enumerate(hunting))
            + ', and from 100 s on between %d and %d, exactly 200 at %s s. ' % (min(a[0] for a in settled), max(a[1] for a in settled), flat)
            + 'With 30%% demand noise the band is wider at every delay but narrows sharply across the same boundary, observed at %.1f s. ' % obs
            + 'Mean pods, red line: ' + ', '.join('%d at %d s' % (a[2], d) for d, a in hunting)
            + ' and %d to %d from 100 s on, that is ' % (min(a[2] for a in settled), max(a[2] for a in settled))
            + _series(['%d%%' % math.floor(100.0 * (a[2] - 200) / 200 + 0.5) for d, a in hunting]) + ' above the need, and then within 1% of it.')
    cap = ('The price of stability at a 90-second dead time and the default window. Blue band: pods from the 5th to the 95th percentile over the last hour, noise-free. '
           'Orange outline: the same band with 30% demand noise. Red: mean pods, noise-free, labelled with its excess over the need. Every quantity changes regime at the same '
           'standing delay, and noise widens the band without moving the boundary.')
    FIGS.append(Figure('cost', s, aria, cap))


def t29():
    lines = section('T29')
    a = {}
    b = {}
    for row in lines:
        m = re.match(r'a (\d+) \| (.*)', row)
        if m:
            a[int(m.group(1))] = [int(v) for v in m.group(2).split()]
        m = re.match(r'b (\d+) \| (.*)', row)
        if m:
            b[int(m.group(1))] = [int(v) for v in m.group(2).split()]
    return a, b


def fig_reach():
    a, _ = t29()
    s = base('chart-reach', 290, ml=(34, 42), mr=(14, 16))
    s['X'] = dict(lo=8, hi=46, ticks=[[v, '%d' % v] for v in (10, 20, 30, 40)], title='replicas already there, ready plus on order', ntitle='replicas, ready + on order')
    s['Y'] = dict(lo=0, hi=23, ticks=[[v, '%d' % v] for v in (0, 5, 10, 15, 20)], title='pods this sync orders', ntitle='pods ordered')
    e = s['els']
    for ready, c in ((10, 'b'), (20, 'd')):
        recs = a[ready]
        pts = [[ready + i, max(0, r - (ready + i))] for i, r in enumerate(recs) if ready + i <= 44]
        e.append(dict(t='line', pts=pts, c=c, w=2.2, mk=2.5))
        e.append(dict(t='vline', x=2 * ready, c=c, dash=True))
        stop = next(x for x, o in pts if o == 0)
        e.append(dict(t='txt', x=ready, y=ready, s='%d ready' % ready, al='left', bl='bottom', dx=4, dy=-6, c=c, b=True))
        e.append(dict(t='txt', x=2 * ready, y=13 if ready == 10 else 15, s='2 x ready = %d' % (2 * ready), n='%d' % (2 * ready), al='left', bl='middle', dx=5, c=c))
        e.append(dict(t='txt', x=stop, y=0, s='stops at %d' % stop, n='', al='left', bl='bottom', dx=4, dy=-6, c=c))
    aria = ('Pods ordered by one sync of the ported CPU calculation against the replicas already there, ready plus on order, with every ready pod at its limit and a '
            '50% target. With 10 ready the sync orders 10 pods when nothing is on order and one fewer for each pod already ordered, reaching zero at 18 replicas, two '
            'short of twice the ready pods. With 20 ready it orders 20, falling to zero at 36 replicas.')
    cap = ('One sync of the ported CPU calculation, swept over the pods already ordered. Every pod on order reduces what the sync orders by one, so the total '
           'never passes twice the ready pods (dashed). The tolerance band stops it a little short: at 18 replicas with 10 ready, and at 36 with 20.')
    FIGS.append(Figure('reach', s, aria, cap))


def fig_backlog_rule():
    _, b = t29()
    s = base('chart-backlog-rule', 300, ml=(34, 42), mr=(14, 16))
    s['X'] = dict(lo=0, hi=5000, ticks=[[v, '{:,}'.format(v)] for v in (0, 1000, 2000, 3000, 4000, 5000)], nticks=[[v, '{:,}'.format(v)] for v in (0, 2500, 5000)], title='backlog, messages', ntitle='backlog')
    s['Y'] = dict(lo=0, hi=520, ticks=[[v, '%d' % v] for v in (0, 100, 200, 300, 400, 500)], title='recommendation, threshold 10 messages per pod', ntitle='recommendation')
    e = s['els']
    cols = {100: 'c', 200: 'b', 300: 'd'}
    xs = list(range(0, 5001, 100))
    for cur in (300, 200, 100):
        pts = [[x, r] for x, r in zip(xs, b[cur])]
        e.append(dict(t='line', pts=pts, c=cols[cur], w=2.6 if cur == 200 else 1.6))
        hold = [x for x, r in zip(xs, b[cur]) if r == cur and x > 0]
        e.append(dict(t='txt', x=hold[-1], y=cur, s='%d replicas: band holds %d' % (cur, cur), n='%d: holds' % cur, al='left', bl='top', dx=6, dy=4, c=cols[cur]))
    e.append(dict(t='txt', x=100, y=480, s='backlog / 10, whatever the replica count', n='backlog / 10', al='left', bl='top', c='ink'))
    aria = ('Recommendation of the ported external per-pod calculation, threshold 10 messages per pod, against backlog from 0 to 5,000 messages, for 100, 200 '
            'and 300 current replicas. All three lines follow backlog divided by 10, from 0 to 500, except for a flat step where each holds its current count: '
            '100 replicas between 900 and 1,100 messages, 200 between 1,800 and 2,200, and 300 between 2,700 and 3,300.')
    cap = ('The ported external per-pod calculation swept over the backlog, for three current replica counts. The recommendation is the backlog divided by '
           'the threshold, whichever count is current, except inside each count\'s tolerance band. Pods on order do not change it: nothing in the signal says they exist.')
    FIGS.append(Figure('backlog-rule', s, aria, cap))




def fig_boundary_window():
    rows = [cells(row) for row in section('T12') if not row.startswith('mean')]
    s = base('chart-boundary-window', 320, ml=(40, 50), mr=(54, 64))
    s['X'] = dict(lo=50, hi=720, log=True, ticks=[[v, '%d s' % v] for v in (60, 120, 300, 600)], title='downscale stabilization window, log scale', ntitle='window (log)')
    s['Y'] = dict(lo=0, hi=180, ticks=[[v, '%d s' % v] for v in (0, 40, 80, 120, 160)], title='standing delay the deployed loop needs', ntitle='delay needed')
    e = s['els']
    cols = {30: 'c', 60: 'b', 90: 'e', 180: 'd'}
    show = {(90, 60), (90, 120), (90, 300), (90, 600), (60, 60), (60, 120)}
    for dead in (30, 60, 90, 180):
        sel = [r for r in rows if int(r[0]) == dead]
        pts = [[number(r[1]), number(r[2])] for r in sel]
        e.append(dict(t='line', pts=pts, c=cols[dead], mk=4, w=2.4 if dead == 90 else 1.6))
        e.append(dict(t='txt', x=pts[-1][0], y=pts[-1][1], s='τ = %d s' % dead, al='left', bl='middle', dx=8, c=cols[dead], b=True))
        for (w, v), r in zip(pts, sel):
            if (dead, int(w)) in show:
                if (dead, int(w)) == (90, 60):
                    e.append(dict(t='txt', x=w, y=v, s='%.1f' % v, n='%.0f' % v, al='right', bl='middle', dx=-8, c=cols[dead]))
                else:
                    e.append(dict(t='txt', x=w, y=v, s='%.1f' % v, n='%.0f' % v if dead == 90 else '', al='center', bl='bottom' if dead == 90 else 'top', dy=-7 if dead == 90 else 7, c=cols[dead]))
    aria = ('Standing delay the deployed loop needs against the downscale window on a log scale, one line per dead time. Dead time 30 s: 27.1, 31.8, 41.1, 51.6 s '
            'for windows of 60, 120, 300 and 600 s. 60 s: 41.1, 49.3, 62.2, 75.0. 90 s: 47.0, 63.3, 85.5, 98.4. 180 s: 57.5, 87.8, 132.2, 166.1. Every line rises with the window.')
    cap = ('The smallest standing delay at which the deployed loop stops hunting, against the window, for four dead times. Every line rises: the window '
           'added to calm the loop raises the delay the loop needs to be calm. Model: ported controller, 15-second sync, demand stepping from 50 to 200 pods needed, '
           'last hour of a 20-hour run.')
    FIGS.append(Figure('boundary-window', s, aria, cap))




# ---------- Part 3 ----------

def fig_trap():
    t6 = [cells(row) for row in section('T6')]
    t16 = [cells(row) for row in section('T16')]
    s = base('chart-trap', 340, ml=(50, 60), mr=(14, 16))
    s['X'] = dict(lo=0.45, hi=1.7, ticks=[[v, '%.1f' % v] for v in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6)], title='amplified utilization A·ρ', ntitle='A·ρ')
    s['Y'] = dict(lo=1000, hi=300000, log=True, ticks=[[1000, '1,000'], [10000, '10,000'], [100000, '100,000']], title='seconds to recover after a 300 s tenfold spike (log)', ntitle='recovery, s (log)')
    e = s['els']
    e.append(dict(t='rect', x0=1.0, x1=1.7, y0=1000, y1=300000, c='a', al=0.10))
    e.append(dict(t='vline', x=1.0, c='a', dash=True))
    e.append(dict(t='txt', x=1.03, y=120000, s='A·ρ ≥ 1: never recovers', n='never recovers', al='left', c='a', b=True))
    curve = [[x, 300 * (10 * x - 1) / (1 - x)] for x in [0.5 + i * 0.005 for i in range(97)]]
    e.append(dict(t='line', pts=curve, c='b', w=2))
    e.append(dict(t='txt', x=0.60, y=2300, s='derived curve, Δ = 300 s', n='derived', al='left', bl='top', c='b'))
    seen = {}
    for r in t6:
        x = number(r[2])
        if r[3] == 'stuck':
            e.append(dict(t='pt', x=x, y=270000, c='a', r=5, open=True))
            continue
        fl = number(r[4])
        des = [number(v) for v in r[5].split()]
        e.append(dict(t='pt', x=x, y=fl, c='ink', r=6, open=True))
        for v in des:
            e.append(dict(t='pt', x=x, y=v, c='d', r=2.5))
        key = round(x, 2)
        if key not in seen:
            seen[key] = 1
            e.append(dict(t='txt', x=x, y=fl, s='%s s' % '{:,}'.format(int(number(r[3]))), n='', al='right', bl='middle', dx=-10, c='b'))
    for r in t16:
        x = number(r[2])
        if r[3] == 'stuck':
            e.append(dict(t='pt', x=x, y=270000, c='a', r=5, open=True))
            continue
        e.append(dict(t='pt', x=x, y=number(r[4]), c='c', r=4.5))
    e.append(dict(t='txt', x=1.2, y=270000, s='stuck in every run: off the scale', n='stuck: off scale', al='center', bl='top', dy=9, c='a'))
    e.append(dict(t='txt', x=0.88, y=19398, s='retry-budget runs', n='budget', al='right', bl='middle', dx=-10, c='c'))
    aria = ('Recovery time after a 300-second tenfold spike against amplified utilization A times rho, log scale. The derived curve rises from 2,400 s at 0.5 to '
            '3,750 s at 0.6, 10,500 s at 0.8, 19,500 s at 0.88 and 64,500 s at 0.96, diverging at 1. Fluid-model points (open circles), request-level runs (small dots) '
            'and retry-budget runs (green) sit on it. At A times rho of 1.0, 1.2, 1.5 and 1.6 every run is stuck.')
    cap = ('Recovery time of a fixed-capacity service after a 300-second tenfold spike, against A·ρ. Blue: the derived formula. Open circles: the fluid model. '
           'Small orange dots: request-level runs, three seeds each. Green: runs with a retry budget instead of capped retries. Right of the red line, every '
           'run stayed failed; those runs are drawn as open circles at the top edge because they have no recovery time to plot.')
    FIGS.append(Figure('trap', s, aria, cap))


def fig_scaler():
    t7 = [cells(row) for row in section('T7')]
    rows = []
    for r in t7:
        tgt = number(r[0]) / 100.0
        pol = r[1].strip()
        if pol.startswith('budget'):
            beta = int(re.search(r'(\d+)%', pol).group(1)) / 100.0
            A = 1 + beta
            name = '%s, retry budget %d%%' % (r[0], round(beta * 100))
        else:
            A = 3
            name = '%s, 2 retries%s' % (r[0], ', backoff 5 s' if 'backoff' in pol else '')
        st = r[3]
        sec = None if 'failed' in st else int(re.search(r'after (\d+) s', st).group(1))
        rows.append((name, A * tgt, sec))
    order = sorted(rows, key=lambda x: (x[2] is None, x[1]))
    n = len(order)
    s = base('chart-scaler', 46 + 34 * n + 46, ml=(10, 10), mr=(14, 16), mt=34, mb=40)
    s['X'] = dict(lo=100, hi=30000, log=True, ticks=[[100, '100 s'], [1000, '1,000 s'], [10000, '10,000 s']], title='time until healthy after a sustained tenfold step (log)', ntitle='time to healthy (log)')
    s['Y'] = dict(lo=0, hi=n, ticks=[], title='first-attempt signal: target and retry policy', ntitle='first-attempt signal')
    e = s['els']
    for i, (name, ar, sec) in enumerate(order):
        y1 = n - i - 0.18
        y0 = n - i - 0.62
        ym = (y0 + y1) / 2
        if sec is None:
            e.append(dict(t='txt', x=30000, y=ym, s='never recovers: trapped', n='never: trapped', al='right', dx=-4, c='a', b=True))
        else:
            e.append(dict(t='pt', x=sec, y=ym, c='b', r=6))
            e.append(dict(t='txt', x=sec, y=ym, s='{:,} s'.format(sec), al='left', dx=10, c='b', b=True))
        e.append(dict(t='txt', x=100, y=y1, s='%s   A·ρ = %.2f' % (name, ar), n='%s  A·ρ %.2f' % (name.replace(', retry budget', ', budget'), ar), al='left', bl='bottom', dy=-2, c='ink'))
    aria = ('Time until healthy after a sustained tenfold step, for an autoscaler driven by first attempts only. Sorted by amplified utilization: retry budget 20% at a '
            '50% target, A times rho 0.60, 274 s; budget 50%, 0.75, 422 s; 2 retries at 25%, 0.75, 384 s; at 30%, 0.90, 922 s; at 33%, 0.99, 8,909 s. Trapped, never '
            'healthy: 2 retries at a 50% target, 1.50, with or without a 5-second backoff.')
    cap = ('An autoscaler that counts first attempts only holds ρ at its target, so it lands at A·ρ = A × target. Every configuration below 1 recovers, more slowly '
           'the closer it gets; every configuration at or above 1 stays trapped, however fast it scaled. Backoff delays retries without removing any, and changes '
           'nothing. Model: sustained tenfold step, 10-second timeout, wasted work.')
    FIGS.append(Figure('scaler', s, aria, cap))




def fig_anatomy():
    rows = {}
    for row in section('T32'):
        m = re.match(r'(\w+)\s*\| (.*)', row)
        rows[m.group(1)] = [tuple(int(v) for v in g.split(',')) for g in re.findall(r'\(([^)]*)\)', m.group(2))]
    for sig, title, fid in (('first', 'first attempts only', 'anatomy-first'), ('ingress', 'ingress rate, retries included', 'anatomy-ingress')):
        d = rows[sig]
        s = base('chart-' + fid, 270, ml=(46, 56), mr=(40, 48))
        s['X'] = dict(lo=0, hi=1200, ticks=[[v, '%d s' % v] for v in (0, 300, 600, 900, 1200)], title='seconds after the tenfold step', ntitle='s after step')
        s['Y'] = dict(lo=0, hi=32000, ticks=[[v, '{:,}'.format(v)] for v in (0, 10000, 20000, 30000)], title='requests served per second', ntitle='served / s')
        s['R'] = dict(lo=0, hi=320, ticks=[[v, '%d' % v] for v in (0, 100, 200, 300)], title='pods', ntitle='pods', col='b')
        e = s['els']
        e.append(dict(t='band', pts=[[t, 0, g] for t, sv, g, z in d], c='c', al=0.55))
        e.append(dict(t='band', pts=[[t, g, g + z] for t, sv, g, z in d], c='a', al=0.40))
        e.append(dict(t='line', ax='R', pts=[[t, sv] for t, sv, g, z in d], c='b', w=2.2))
        peak = max(d, key=lambda r: r[1])
        last = d[-1]
        e.append(dict(t='txt', ax='R', x=last[0], y=last[1], s='%d pods' % last[1], al='right', bl='bottom', dy=-5, c='b', b=True))
        if sig == 'first':
            e.append(dict(t='txt', x=700, y=last[3] / 2, s='every pod busy with abandoned attempts: good work 0', n='all wasted, good 0', al='center', bl='middle', c='ink'))
        else:
            e.append(dict(t='txt', ax='R', x=peak[0], y=peak[1], s='%d pods clear the debt' % peak[1], n='%d pods' % peak[1], al='left', bl='bottom', dx=6, dy=-4, c='b'))
            e.append(dict(t='txt', x=900, y=last[2] / 2, s='good work: all 5,000 requests a second', n='good 5,000/s', al='center', bl='middle', c='ink'))
        FIGS.append((fid, s))
    aria_f = ('First-attempt scaler after a tenfold step, over 1,200 seconds. Pods rise to 100 by 150 seconds and stay there. From then on, all of the 10,000 '
              'requests served each second are abandoned attempts; good work stays at zero.')
    aria_i = ('Ingress-rate scaler after the same step. Pods rise to 300 by 180 seconds, the work served is all abandoned attempts until between 240 and 270 seconds, then good work returns to '
              'all 5,000 requests a second, wasted work falls to zero, and pods fall back to 100.')
    cap_f = ('The first-attempt scaler. Red: abandoned attempts served each second; green: good work; blue, right axis: pods. The right axis is scaled at 100 requests a '
             'second per pod, so the pod line also reads as capacity. It provisions exactly the need, and the need is spent entirely on debt. Model: 10-second timeout, two '
             'retries, abandoned work still served.')
    cap_i = ('The ingress-rate scaler under the same step and on the same scales. It sees the retries, buys three times the need, clears the debt within about five '
             'minutes, and returns to the need once good work is flowing. The pod line again reads as capacity on the left axis.')
    out = []
    for f in FIGS:
        if f[0] == 'anatomy-first':
            out.append(Figure('anatomy-first', f[1], aria_f, cap_f))
        elif f[0] == 'anatomy-ingress':
            out.append(Figure('anatomy-ingress', f[1], aria_i, cap_i))
        else:
            out.append(f)
    FIGS[:] = out




# ---------- Part 4 ----------

def fig_ceiling():
    rows = [cells(row) for row in section('T17')]
    s = base('chart-ceiling', 320, ml=(50, 60), mr=(14, 16))
    s['X'] = dict(lo=12, hi=42, ticks=[[v, '%d' % v] for v in (15, 20, 25, 30, 35, 40)], title='replica ceiling M, pods', ntitle='ceiling M')
    s['Y'] = dict(lo=1000, hi=200000, log=True, ticks=[[1000, '1,000'], [10000, '10,000'], [100000, '100,000']], title='seconds to recover after the spike (log)', ntitle='recovery, s (log)')
    e = s['els']
    e.append(dict(t='rect', x0=12, x1=15, y0=1000, y1=200000, c='a', al=0.10))
    e.append(dict(t='vline', x=15, c='a', dash=True))
    e.append(dict(t='txt', x=15.6, y=1350, s='at or below 15 = A × need: trapped', n='M ≤ 15: trapped', al='left', c='a', b=True))
    e.append(dict(t='txt', x=14.85, y=180000, s='stuck: off scale', n='off scale', al='right', bl='top', dy=9, c='a'))
    rec = [(int(r[0]), number(r[2])) for r in rows if r[1] == 'recovers']
    const = math.fsum(t * (m - 15) for m, t in rec) / len(rec)
    curve = [[m, const / (m - 15)] for m in [15.2 + i * 0.1 for i in range(270)] if const / (m - 15) <= 200000]
    e.append(dict(t='line', pts=curve, c='g', w=1.2, dash=True))
    e.append(dict(t='txt', x=33, y=const / 18, s='about %s / (M − 15) seconds' % '{:,}'.format(int(round(const, -2))), n='~1/(M − 15)', al='left', bl='bottom', dy=-6, c='g'))
    for r in rows:
        m = int(r[0])
        if r[1] != 'recovers':
            e.append(dict(t='pt', x=m, y=180000, c='a', r=5, open=True))
    for m, t in rec:
        e.append(dict(t='pt', x=m, y=t, c='b', r=5))
        e.append(dict(t='txt', x=m, y=t, s='{:,} s'.format(int(t)), al='right' if m >= 35 else 'left', bl='top' if m >= 35 else 'bottom', dx=-6 if m >= 35 else 6, dy=8 if m >= 35 else -6, c='b'))
    aria = ('Recovery time after a tenfold 300-second spike against the replica ceiling, with two retries and a CPU signal; the amplified load needs 15 pods. '
            'Ceilings of 14 and 15 never recover. A ceiling of 16 recovers after 40,293 seconds, 20 after 7,921, 25 after 3,925 and 40 after 1,530, '
            'close to a constant divided by the margin above 15.')
    cap = ('A replica ceiling against the amplified load. With two retries the failing service needs 15 pods to drain; at or below that ceiling it never '
           'recovers, drawn as open circles at the top edge, and above it recovery time falls roughly as one over the margin. Model: CPU signal, 10-second timeout, two retries, abandoned work served.')
    FIGS.append(Figure('ceiling', s, aria, cap))


def fig_time_vs_size():
    rows = [cells(row) for row in section('T9')]
    def get(alpha, cfg, qty):
        r = [x for x in rows if x[0] == alpha and x[1] == cfg and x[2] == qty][0]
        return [number(r[3]), number(r[4]), number(r[5])]
    K = get('1.5', 'no bound', 'K')
    tc = get('1.5', 'no bound', 't_cap')
    tcf = get('1.5', 'bound 5 s first', 't_cap')
    names = ['median', '90th', '99th']
    s = base('chart-time-size', 300, ml=(44, 54), mr=(14, 16))
    s['X'] = dict(lo=1.5, hi=60, log=True, ticks=[[2, '2x'], [5, '5x'], [10, '10x'], [20, '20x'], [50, '50x']], title='overload K at the median, 90th and 99th percentile (log scale)', ntitle='overload K (log)')
    s['Y'] = dict(lo=0, hi=560, ticks=[[v, '%d s' % v] for v in (0, 100, 200, 300, 400, 500)], title='time until capacity meets the load, same percentile', ntitle='time to capacity')
    e = s['els']
    e.append(dict(t='line', pts=[[k, t] for k, t in zip(K, tc)], c='b', mk=5))
    e.append(dict(t='line', pts=[[k, t] for k, t in zip(K, tcf)], c='c', mk=5))
    for k, t, nm in zip(K, tc, names):
        if nm != 'median':
            e.append(dict(t='txt', x=k, y=t, s='%s: %.1fx, %d s' % (nm, k, t), n='%d s' % t, al='right', bl='bottom', dx=-8, dy=-4, c='b'))
    for k, t, nm in zip(K, tcf, names):
        e.append(dict(t='txt', x=k, y=t, s=('median: %.1fx, %d s, both' % (k, t)) if nm == 'median' else '%d s' % t, n='%d s' % t, al='left' if nm == 'median' else 'center', bl='top', dy=8, c='c'))
    e.append(dict(t='txt', x=K[1], y=tc[1], s='CPU signal', al='left', bl='top', dx=10, dy=8, c='b', b=True))
    e.append(dict(t='txt', x=K[2], y=tcf[2], s='first attempts, 5 s bound', n='bounded', al='right', bl='bottom', dx=-8, dy=-6, c='c', b=True))
    aria = ('Time until capacity meets the load against the overload, at the median, 90th and 99th percentile of 3,000 Pareto overloads with tail index 1.5, overload on a '
            'log scale. CPU signal: 105 s at 2.3x, 240 s at 6.9x, 480 s at 31.3x. First-attempt signal behind a 5-second admission bound: 105, 120 and 135 s at the same '
            'overloads.')
    cap = ('Size against time under heavy-tailed overloads, at matching percentiles. On a log scale for the overload, the CPU signal\'s points lie close to a straight line: '
           'time grows with the logarithm of size, about fourteenfold more overload for less than five times the time. Behind an admission bound the first-attempt '
           'signal barely moves. Model: CPU run without timeouts or retries; bounded run with a 10-second timeout and two retries.')
    FIGS.append(Figure('time-size', s, aria, cap))




def fig_tail():
    rows = [cells(row) for row in section('T35')] + [cells(row) for row in section('T43')]
    t9 = [cells(row) for row in section('T9')]
    pure = [x for x in t9 if x[0] == '1.5' and x[1] == 'no bound' and x[2] == 'backlog'][0]
    pure99 = number(pure[5])
    xs = {'none': 1, '60 s': 2, '20 s': 3, '12 s': 4, '8 s': 5, '5 s': 6, '2 s': 7}
    rows.sort(key=lambda r: xs[r[0]])
    pts_b, pts_l = [], []
    for r in rows:
        b99 = number(r[1].split('/')[2])
        l99 = number(r[2].split('/')[2])
        pts_b.append([xs[r[0]], b99])
        pts_l.append([xs[r[0]], l99])
    s = base('chart-tail', 330, ml=(54, 64), mr=(14, 16))
    s['X'] = dict(lo=0.6, hi=7.4, ticks=[[1, 'no bound'], [2, '60 s'], [3, '20 s'], [4, '12 s'], [5, '8 s'], [6, '5 s'], [7, '2 s']], nticks=[[1, 'none'], [2, '60'], [3, '20'], [4, '12'], [5, '8'], [6, '5'], [7, '2']], title='admission bound, seconds of capacity the queue may hold (not to scale)', ntitle='bound, s')
    s['Y'] = dict(lo=10, hi=200000, log=True, ticks=[[10, '10'], [100, '100'], [1000, '1,000'], [10000, '10,000'], [100000, '100,000']], title='99th percentile, seconds of the original load (log)', ntitle='p99, s of load (log)')
    e = s['els']
    e.append(dict(t='rect', x0=4.5, x1=7.4, y0=10, y1=200000, c='c', al=0.08))
    e.append(dict(t='vline', x=4.5, c='c', dash=True))
    e.append(dict(t='txt', x=4.55, y=130000, s='bound below the 10 s timeout', n='below timeout', al='left', c='c', b=True))
    e.append(dict(t='hline', y=pure99, c='g', w=1, dash=True))
    e.append(dict(t='txt', x=0.65, y=pure99, s='queue without retries: %s' % '{:,}'.format(int(round(pure99))), n='no retries: %s' % '{:,}'.format(int(round(pure99))), al='left', bl='top', dy=4, c='g'))
    # The bounds are categories at equal spacing, not a scale, so the points are not joined:
    # a line between them would suggest a gradient the sweep does not measure.
    for x, v in pts_b:
        e.append(dict(t='pt', x=x, y=v, c='b', r=5))
    for x, v in pts_l:
        e.append(dict(t='pt', x=x, y=v, c='a', r=5, open=True))
    for (x, v) in pts_b:
        if x == 4:
            e.append(dict(t='txt', x=x, y=v, s='{:,}'.format(int(round(v))), al='right', bl='middle', dx=-10, c='b'))
            continue
        e.append(dict(t='txt', x=x, y=v, s='{:,}'.format(int(round(v))), al='center', bl='bottom' if x == 1 else 'top', dy=-8 if x == 1 else 8, c='b'))
    for (x, v) in pts_l:
        e.append(dict(t='txt', x=x, y=v, s='{:,}'.format(int(round(v))), n='{:,}'.format(int(round(v))) if x in (1, 4, 5) else '', al='center', bl='top' if x == 1 else 'bottom', dy=8 if x == 1 else -8, c='a'))
    e.append(dict(t='txt', x=2.5, y=75000, s='rejected or lost', al='center', c='a', b=True))
    e.append(dict(t='txt', x=0.9, y=300, s='peak backlog', al='left', c='b', b=True))
    aria = ('99th percentiles over 3,000 Pareto overloads with tail index 1.5, CPU signal, 10-second timeout, two retries, by admission bound. Peak backlog: 50,563 with no '
            'bound, 27,181 at 60 s, 9,810 at 20 s, 1,633 at 12 s, 190 at 8 s, 113 at 5 s and 32 at 2 s. Rejected or lost: 30,905, 29,088, 26,080, 22,064, 10,979, 11,056 and 11,137. '
            'Between 12 s and 8 s, either side of the timeout, the loss halves. A dashed line at 11,170 marks the peak backlog of the same overloads with no timeouts or retries at all. Filled points are peak backlog, open points rejected or lost; the bounds are categories, so the points are not joined.')
    cap = ('What an admission bound does to the tail, in 99th percentiles over 3,000 heavy-tailed overloads. Bounds longer than the client timeout leave the debt in place and '
           'barely change what is lost, even at 12 seconds, just above the timeout. Bounds shorter than the timeout remove the debt: the backlog collapses, and what is rejected falls to almost exactly what a queue with '
           'no retries would have held, the size of the overload itself. Model: CPU signal, 10-second timeout, two retries.')
    FIGS.append(Figure('tail', s, aria, cap))


def fig_staircase():
    runs = {}
    for row in section('T18'):
        k, rest = row.split('|', 1)
        runs[k.strip()] = [tuple(int(v) for v in m.split(',')) for m in re.findall(r'\(([\d,]+)\)', rest)]
    tmax = 780
    cols = {'3x': 'c', '10x': 'b', '30x': 'a'}
    need = {'3x': 15, '10x': 50, '30x': 150}
    s = base('chart-staircase', 340, ml=(36, 48), mr=(34, 44))
    s['X'] = dict(lo=0, hi=tmax, ticks=[[t, '%d s' % t] for t in (0, 120, 240, 360, 480, 600, 720)],
                  nticks=[[t, '%d s' % t] for t in (0, 240, 480, 720)], title='seconds after the step', ntitle='seconds after the step')
    s['Y'] = dict(lo=8, hi=1600, log=True, ticks=[[n, str(n)] for n in (10, 20, 40, 80, 160, 320, 640, 1280)],
                  title='pods ordered, doubling scale', ntitle='pods ordered, doubling scale')
    e = s['els']
    for k in cols:
        e.append(dict(t='hline', y=need[k], c=cols[k], w=1, dash=True))
    for k in reversed(list(cols)):              # 30x first, so the shared trunk shows the smallest run on top
        pts = []
        for t, n, _ in runs[k]:
            if t > tmax:
                break
            if pts:
                pts.append([t, pts[-1][1]])
            pts.append([t, n])
        pts.append([tmax, pts[-1][1]])
        e.append(dict(t='line', pts=pts, c=cols[k], w=2))
        e.append(dict(t='txt', x=tmax, y=pts[-1][1], s=k, al='left', dx=5, c=cols[k], b=True))
    e.append(dict(t='txt', x=8, y=120, s='all three runs share one line until 150 s', n='one line until 150 s', al='left', c='ink'))
    e.append(dict(t='txt', x=34, y=12.3, s='16 first: the 30 s window is half full at the first sync', n='', al='left', c='sub'))
    e.append(dict(t='txt', x=8, y=1000, s='dashed: pods at which capacity first meets each load', n='dashed: capacity meets load', al='left', c='sub'))
    aria = ('Pods ordered against time for overloads of three, ten and thirty times, on a doubling scale. All three lines are identical for the first 150 seconds: '
            '10 pods, then 20 ordered, then 40 ordered. The three-times line stops at 40 and later falls to 30. The ten-times line continues to 80, 159 and 317. '
            'The thirty-times line continues to 630 and then past 1,000. Dashed lines mark the pods at which capacity first meets each load: 15, 50 and 150.')
    cap = ('Pods ordered after a load step of 3x, 10x and 30x in the running specimen, on a doubling scale. The first two orders are identical in all three runs: '
           'the saturated metric reads the same, so the controller asks for the same. A run separates from the others only after its capacity has met its load, and '
           'each keeps climbing past its dashed line while the backlog drains.')
    FIGS.append(Figure('staircase', s, aria, cap))


def fig_hunt():
    rows = {}
    for row in section('T24'):
        a, b = row.split('|')
        rows[int(a.split()[0])] = [int(v) for v in b.split()]
    def steps(values):
        pts = []
        for i, v in enumerate(values):
            pts += [[i, v], [i + 1, v]]
        return pts
    s = base('chart-hunt', 340, ml=(34, 44), mr=(12, 12))
    s['X'] = dict(lo=0, hi=60, ticks=[[m, '%d min' % m] for m in (0, 10, 20, 30, 40, 50, 60)],
                  nticks=[[m, '%d min' % m] for m in (0, 20, 40, 60)], title='minutes into the last hour', ntitle='minutes into the last hour')
    s['Y'] = dict(lo=0, hi=420, ticks=[[n, str(n)] for n in (0, 100, 200, 300, 400)], title='pods', ntitle='pods')
    e = s['els']
    e.append(dict(t='line', pts=steps(rows[60]), c='a', w=2))
    e.append(dict(t='line', pts=steps(rows[150]), c='c', w=2.4))
    e.append(dict(t='txt', x=60, y=350, s='standing delay 60 s: the loop hunts', n='60 s: hunts', al='right', bl='bottom', dy=-6, c='a', b=True))
    e.append(dict(t='txt', x=60, y=26, s='green, standing delay 150 s: rests at the need all hour', n='green, 150 s: rests', al='right', bl='middle', c='c', b=True))
    e.append(dict(t='txt', x=11.2, y=350, s='window holds the peak, 6 to 7 min', n='window holds the peak', al='left', bl='bottom', dy=-6, c='ink'))
    e.append(dict(t='txt', x=8.6, y=56, s='released: collapse', n='release', al='left', bl='top', dy=3, c='ink'))
    aria = ('Pods over the last hour of a twenty-hour run with flat demand needing 200 pods, sampled every minute. Standing delay 60 seconds, in red: the count sits '
            'at 350 pods for six to seven minutes, drops within two minutes to between 56 and 124 pods, climbs back over the next two to three minutes, and repeats '
            'about every ten minutes. Standing delay 150 seconds, in green: the count stays at exactly 200 for the whole hour.')
    cap = ('Pods each minute over the last hour of a twenty-hour run, with demand flat at two hundred pods\' worth, a 90-second dead time and the default '
           '300-second window. Red, a standing delay of 60 seconds: the loop hunts in a regular cycle. The window holds each peak for six to seven minutes, the '
           'count collapses when it lets go, and the rebuild waits on the dead time. Green, 150 seconds: the count sits at the need all hour.')
    FIGS.append(Figure('hunt', s, aria, cap))



def fig_map():
    rows = [cells(row) for row in section('T48')]
    pts = [(r[0], number(r[4]), number(r[5]), r[6] == 'failed') for r in rows]
    by = {name: (x, y, failed) for name, x, y, failed in pts}
    healthy = [(name, x, y) for name, x, y, failed in pts if not failed]
    frontier = sorted((name, x, y) for name, x, y in healthy if not any(x2 <= x and y2 <= y and (x2, y2) != (x, y) for _, x2, y2 in healthy))
    frontier.sort(key=lambda t: t[1])
    colour = {'cpu': 'b', 'ingress': 'b', 'pair': 'b', 'first': 'a', 'first, target 30%': 'd', 'first, target 25%': 'd',
              'first, budget 20%': 'e', 'first, budget 50%': 'e', 'first, bound 5 s': 'c', 'cpu, bound 5 s': 'c'}
    label = {'cpu': 'CPU', 'ingress': 'ingress and pair', 'first': 'first attempts alone: still failing after an hour',
             'first, target 30%': 'target 30%', 'first, target 25%': 'target 25%', 'first, budget 20%': 'budget 20%',
             'first, budget 50%': 'budget 50%', 'first, bound 5 s': 'bound 5 s', 'cpu, bound 5 s': 'CPU, bound 5 s'}
    short = dict(label, ingress='ingress, pair', first='first attempts alone', **{'cpu, bound 5 s': 'CPU, bound'})
    s = base('chart-map', 360, ml=(44, 54), mr=(14, 16))
    s['X'] = dict(lo=1.0, hi=5.3, ticks=[[1, '1'], [2, '2'], [3, '3'], [4, '4'], [5, '5']], title='pods held over the hour, per pod of stepped demand at full rate', ntitle='pods held per pod of demand')
    s['Y'] = dict(lo=50, hi=6000, log=True, ticks=[[100, '100 s'], [1000, '1,000 s']], title='first-attempt work lost, seconds of the stepped demand (log)', ntitle='work lost (log)')
    e = s['els']
    e.append(dict(t='line', pts=[[x, y] for _, x, y in frontier], c='c', w=1.5, dash=True))
    for name, (x, y, failed) in by.items():
        if name == 'pair':
            continue
        e.append(dict(t='pt', x=x, y=y, c=colour[name], r=5, open=failed))
        left = name in ('cpu, bound 5 s', 'cpu', 'first, target 25%', 'first, target 30%', 'first, budget 20%', 'first, budget 50%')
        e.append(dict(t='txt', x=x, y=y, s=label[name], n=short[name], al='right' if left else 'left', dx=-9 if left else 9, c=colour[name]))
    e.append(dict(t='txt', x=frontier[0][1], y=60, s='dashed: the frontier, no configuration has fewer pods and less loss', n='dashed: frontier', al='left', c='c'))
    e.append(dict(t='txt', x=5.25, y=4500, s='a scaler on first attempts unless marked CPU, ingress or pair', n='first attempts unless marked', al='right', c='sub'))
    def say(name):
        x, y, failed = by[name]
        full = name.replace('cpu', 'CPU').replace('first', 'first attempts')
        return '%s %.2f pods and %s s lost%s' % (full, x, '{:,}'.format(int(y)), ' with the service still failing' if failed else '')
    aria = ('Every signal and lever under the same sustained tenfold step, on common axes: pods held over the hour after the step per pod of stepped demand at full rate, '
            'against first-attempt work lost in seconds of the stepped demand. ' + '; '.join(say(n) for n in by if n != 'pair')
            + '. The pair signal coincides with ingress. The frontier runs through ' + _series([n.replace('cpu', 'CPU').replace('first', 'first attempts') for n, _, _ in frontier]) + '.')
    cap = ('Parts 3 and 4 on one map, for a sustained tenfold step with a 10-second timeout: each signal and lever by the pods it holds per pod of demand and the work it loses. '
           'Only the two configurations behind an admission bound reach the frontier; every colder target, retry budget and unbounded signal holds more pods, loses more work, or both. '
           'Model: 90-second dead time, fluid queue, abandoned work served, first hour after the step.')
    FIGS.append(Figure('map', s, aria, cap))


def fig_hill():
    rows = [cells(row) for row in section('T49')]
    series = {}
    for r in rows:
        lo, hi = (number(v) for v in r[3].split('..'))
        series.setdefault(r[0], []).append((number(r[1]), number(r[2]), lo, hi))
    k, bl, lost = series['K, the overload'], series['peak backlog, no bound'], series['refused or lost, bound 5 s']
    s = base('chart-hill', 320, ml=(36, 44), mr=(14, 16))
    s['X'] = dict(lo=0.017, hi=0.36, log=True, ticks=[[0.02, '2%'], [0.05, '5%'], [0.1, '10%'], [0.2, '20%'], [0.3, '30%']], title='share of the 3,000 overloads treated as the tail (log)', ntitle='tail share (log)')
    s['Y'] = dict(lo=0.5, hi=2.3, ticks=[[0.5, '0.5'], [1.0, '1.0'], [1.5, '1.5'], [2.0, '2.0']], title='Hill estimate of the tail index', ntitle='Hill estimate')
    e = s['els']
    e.append(dict(t='hline', y=1.5, c='g', w=1, dash=True))
    e.append(dict(t='txt', x=0.35, y=1.5, s='true index of the overload, 1.5', n='true 1.5', al='right', bl='top', dy=4, c='g'))
    e.append(dict(t='vline', x=0.1, c='sub', dash=True))
    for data, c in ((k, 'b'), (bl, 'a')):
        e.append(dict(t='band', pts=[[x, lo, hi] for x, _, lo, hi in data], c=c, al=0.18))
        e.append(dict(t='line', pts=[[x, y] for x, y, _, _ in data], c=c, w=2, mk=3.5))
    e.append(dict(t='line', pts=[[x, y] for x, y, _, _ in lost], c='d', w=1.5, dash=True))
    e.append(dict(t='txt', x=0.019, y=2.22, s='overload K', al='left', c='b', b=True))
    e.append(dict(t='txt', x=0.019, y=0.74, s='peak backlog, no bound', n='backlog', al='left', c='a', b=True))
    e.append(dict(t='txt', x=0.019, y=0.6, s='dashed: refused or lost behind a 5 s bound', n='dashed: refused, 5 s bound', al='left', c='d'))
    def at10(data):
        """The row of a series at the 10% tail share, the one the text quotes."""
        return [t for t in data if t[0] == 0.1][0]

    aria = ('Hill estimates of the tail index over 3,000 Pareto overloads with true index 1.5, with 90% bootstrap bands, as the share of the sample treated as the tail runs from 2% to 30%. '
            'Overload K: ' + ', '.join('%.2f at %d%%' % (y, round(100 * x)) for x, y, _, _ in k) + '. '
            'Peak backlog with no bound: ' + ', '.join('%.2f at %d%%' % (y, round(100 * x)) for x, y, _, _ in bl) + '. '
            'At the 10%% share the bands are %.2f to %.2f and %.2f to %.2f and do not overlap. ' % (at10(k)[2], at10(k)[3], at10(bl)[2], at10(bl)[3])
            + 'Refused or lost work behind a 5-second bound follows the backlog at every share, %.2f at 10%%.' % at10(lost)[1])
    cap = ('How sure the tail indices are. Bands are 90% bootstrap intervals; the dotted line marks the 10% share the text quotes. The backlog\'s estimate stays below the overload\'s at every share, '
           'and the gap is not sampling noise; it narrows as the tail considered gets deeper, as the logarithm in the backlog\'s growth predicts. '
           'Model: CPU signal, sustained Pareto steps, one hour each.')
    FIGS.append(Figure('hill', s, aria, cap))

BUILDERS = (fig_stale, fig_staircase_stats, fig_staircase, fig_frontier, fig_hottest, fig_efficiency, fig_phi, fig_agreement, fig_cost, fig_hunt, fig_reach, fig_backlog_rule, fig_boundary_window, fig_trap, fig_scaler, fig_anatomy, fig_ceiling, fig_time_vs_size, fig_tail, fig_map, fig_hill)


def figures(results_path):
    """Build every figure from the results file at results_path, in a fixed order."""
    RESULTS.clear()
    RESULTS.update(read(results_path))
    FIGS.clear()
    for build in BUILDERS:
        build()
    return list(FIGS)
