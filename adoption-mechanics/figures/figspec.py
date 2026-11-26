"""Figure specifications for Adoption Mechanics, built from the frozen results.

Every plotted number is parsed from the results file, so a figure cannot drift from the executed code. A
specification is a plain dict (id, height, margins, axes X, Y and optional R, and a list of elements); the
shared canvas engine draws it for the posts and tools/svg.py for the repository. A figure laid out as a table
(table) has no axes: x runs from 0 to 100 across the width and y counts rows from the bottom.

  figures(results_path) -> list of Figure(name, spec, aria, caption)
"""
import math

from results import cells, number, read, rows
from svg import Figure

RESULTS = {}
FIGS = []

def section(tag):
    """The rows of one section of the results being drawn."""
    return rows(RESULTS[tag])


def base(fid, h, ml=(40, 50), mr=(14, 16), mt=24, mb=42):
    """An empty specification: id, height, margins (narrow, wide) and no elements yet."""
    return dict(id=fid, h=h, ml=list(ml), mr=list(mr), mt=mt, mb=mb, els=[])


def table(fid, h, rows):
    """An empty specification laid out as a table: no axes, x from 0 to 100 across the width and y from 0 at the
    bottom to `rows` at the top, so that row r (0 is the header) spans y from rows - r - 1 to rows - r."""
    s = base(fid, h, ml=(8, 8), mr=(8, 8), mt=8, mb=8)
    s['X'] = dict(lo=0.0, hi=100.0, ticks=[], title='', ntitle='')
    s['Y'] = dict(lo=0.0, hi=float(rows), ticks=[], title='', ntitle='')
    return s


def rule(s, y):
    """A thin horizontal rule across the table at height y."""
    s['els'].append(dict(t='hline', y=y, c='grid'))


LEVER_NAMES = {'pilot': 'reversible pilot', 'gate': 'one exterior gate removed', 'poll': 'blind poll',
               'champion': 'insured champion speaks first', 'decorrelate': 'decorrelated panel', 'layers': 'flatter chain'}


def fig_frontier():
    """Part 1: what each lever buys, alone and all six together, as how often a review adopts a better and a worse
    design against today's review (T18)."""
    rows = [cells(r) for r in section('T18')]
    hull = [r for r in rows if r[0].startswith('status quo inside the hull')][0]
    named = {r[0]: (number(r[1]), number(r[2])) for r in rows if not r[0].startswith('status quo inside')}
    six = 'pilot+gate+poll+champion+decorrelate+layers'
    labels = {'pilot': 'Reversible pilot', 'gate': 'One gate removed', 'poll': 'Blind vote',
              'champion': 'Champion speaks first', 'decorrelate': 'Decorrelated panel', 'layers': 'Fewer hand-offs'}
    today = named['baseline']
    apart = [k for k in labels if (named[k][0] - today[0]) * (named[k][1] - today[1]) < 0]
    assert apart == ['decorrelate'], apart
    singles = sorted(labels, key=lambda k: -(named[k][0] - named[k][1]))
    order = [('Today', today)] + [(labels[k], named[k]) for k in singles] + [('All six levers', named[six]),
                                                                            ('Status quo in the hull', (number(hull[1]),
                                                                                                        number(hull[2])))]
    n = len(order)
    s = base('chart-frontier', 60 + 30 * n, ml=(132, 150), mr=(14, 18), mt=8, mb=36)
    s['X'] = dict(lo=0.0, hi=1.0, ticks=[[v, '%d%%' % round(100 * v)] for v in (0.0, 0.25, 0.5, 0.75, 1.0)],
                  title='share of reviews that adopt the design', ntitle='share adopted')
    s['Y'] = dict(lo=-0.6, hi=n + 0.6, ticks=[[n - 1 - i, lab] for i, (lab, _) in enumerate(order)], title='')
    e = s['els']
    e += [dict(t='line', pts=[[today[0], -0.5], [today[0], n - 0.5]], c='b', w=1, dash=True),
          dict(t='line', pts=[[today[1], -0.5], [today[1], n - 0.5]], c='a', w=1, dash=True),
          dict(t='pt', x=0.02, y=n + 0.2, r=4, c='b'),
          dict(t='txt', x=0.02, y=n + 0.2, s='a better design adopted', n='better adopted', al='left', bl='middle', dx=8, c='b'),
          dict(t='pt', x=0.4, y=n + 0.2, r=4, c='a'),
          dict(t='txt', x=0.4, y=n + 0.2, s='a worse design adopted', n='worse adopted', al='left', bl='middle', dx=8, c='a'),
          dict(t='txt', x=0.98, y=n + 0.2, s='dotted: today', n='dotted: today', al='right', bl='middle', c='sub')]
    for i, (lab, (g, bd)) in enumerate(order):
        y = n - 1 - i
        if g == 0 and bd == 0:
            e += [dict(t='pt', x=0.0, y=y, r=5, c='g'),
                  dict(t='txt', x=0.0, y=y, s='nothing passes, better or worse', n='nothing passes', al='left',
                       bl='middle', dx=10, c='sub', b=True)]
            continue
        e += [dict(t='line', pts=[[bd, y], [g, y]], c='g', w=3),
              dict(t='pt', x=bd, y=y, r=5, c='a'), dict(t='pt', x=g, y=y, r=5, c='b'),
              dict(t='txt', x=g, y=y, s='%d%%' % round(100 * g), al='left', bl='middle', dx=8, c='b', b=True),
              dict(t='txt', x=bd, y=y, s='%d%%' % round(100 * bd), al='right', bl='middle', dx=-8, c='a')]
    aria = ('How often a review adopts a better and a worse design: today, with each lever alone, with all six, and '
            'with the status quo inside the approvers\' hull. ' +
            ' '.join('%s: better %d%%, worse %d%%.' % (lab, round(100 * g), round(100 * bd)) for lab, (g, bd) in order))
    cap = ("What each choice buys. Blue is how often a review adopts a better design, red how often it adopts a worse "
           "one, and the dotted lines mark today's %d%% and %d%%. Five levers move both dots the same way; only the "
           "decorrelated panel moves them apart, which is why every widest gap includes it. All six together keep a "
           "better design near %d%% and cut a worse one to %d%%. With the status quo inside the approvers' hull, "
           "nothing passes." % (round(100 * today[0]), round(100 * today[1]), round(100 * named[six][0]),
                                round(100 * named[six][1])))
    FIGS.append(Figure('frontier', s, aria, cap))


def fig_correlation():
    """Part 2: how often stronger models share a mistake, overall and within question difficulty (T13, T19)."""
    series = {'MMLU': [cells(r) for r in section('T13') if not r.strip().startswith('5 strata')]}
    for r in section('T19'):
        c = cells(r)
        if len(c) > 3:
            series.setdefault(c[0], []).append(c[1:])
    colors = {'MMLU': 'b', 'GPQA': 'a', 'MMLU-Pro': 'c'}
    xs = [1, 2, 3, 4, 5]
    lines = {n: ([number(r[4]) for r in series[n]], [number(r[5]) for r in series[n]]) for n in ('MMLU', 'GPQA', 'MMLU-Pro')}
    top = max(max(v[0]) for v in lines.values())
    s = base('chart-correlation', 340, ml=(36, 44), mr=(62, 74))
    s['X'] = dict(lo=0.7, hi=5.3, ticks=[[1, 'weakest'], [2, '2nd'], [3, '3rd'], [4, '4th'], [5, 'strongest']],
                  title='fifth of model pairs, by accuracy', ntitle='fifth of pairs')
    s['Y'] = dict(lo=0.0, hi=5 * math.ceil(top / 5), ticks=[[v, '%d' % v] for v in range(0, 5 * math.ceil(top / 5) + 1, 5)],
                  title='odds the two models share a mistake, against independent errors', ntitle='odds of a shared mistake')
    e = s['els']
    e.append(dict(t='hline', y=1.0, c='g', w=1, dash=True))
    for name in ('MMLU', 'GPQA', 'MMLU-Pro'):
        pooled, within = lines[name]
        e.append(dict(t='line', pts=[[x, v] for x, v in zip(xs, within)], c='g', w=1.5, dash=True, mk=2.5))
        e.append(dict(t='line', pts=[[x, v] for x, v in zip(xs, pooled)], c=colors[name], w=2.5, mk=3.5))
        e.append(dict(t='txt', x=5, y=pooled[-1], s=name, n=name, al='left', bl='middle', dx=8, c=colors[name], b=True))
    e.append(dict(t='txt', x=0.8, y=2.2, s='grey: compared on questions of similar difficulty', n='grey: same difficulty',
                  al='left', bl='bottom', c='g'))
    aria = ('Odds that two language models make the same mistake, against independent errors, by fifth of model pairs '
            'ordered by accuracy, on three benchmarks from Stanford HELM. ' + ' '.join(
                '%s, all questions: %s; questions of similar difficulty: %s.' % (
                    n, ', '.join('%.2f' % v for v in lines[n][0]), ', '.join('%.2f' % v for v in lines[n][1]))
                for n in ('MMLU', 'GPQA', 'MMLU-Pro')))
    cap = ('What stronger models share. The better two models are, the likelier they make the same mistake: for the '
           'strongest fifth of pairs the odds are %.0f, %.0f and %.0f times those of independent errors on three benchmarks. '
           'Compared on questions of similar difficulty, the grey lines, most of that disappears: hard questions are hard '
           'for every model. What remains for the strongest pairs, %.1f to %.1f times, is blind spots of their own.'
           % (lines['MMLU'][0][-1], lines['GPQA'][0][-1], lines['MMLU-Pro'][0][-1],
              min(v[1][-1] for v in lines.values()), max(v[1][-1] for v in lines.values())))
    FIGS.append(Figure('correlation', s, aria, cap))


def fig_lifecycle():
    """Part 1: where reviews of a better and a worse design end, in each of four settings (T26)."""
    names = {'groups decide apart': 'Groups decide apart', 'the groups meet in one room': 'One room',
             'one room, the champion speaks first': 'One room, champion first',
             "one room, the champion speaks first, the status quo among the approvers' priorities":
                 'Status quo among priorities'}
    data = {}
    for r in section('T26'):
        c = cells(r)
        if c[0] in names and len(c) == 6:
            data[(c[0], c[1].split()[0])] = [number(v.split()[-1]) for v in c[2:6]]
    stages = [('stopped in the team review', 'g'), ('lost in the hand-off', 'd'), ('stopped at the approvals', 'e')]

    def pc(v):
        return '%.0f%%' % (100 * v)
    order = list(names)
    n = 3 * len(order)
    s = base('chart-lifecycle', 70 + 22 * n, ml=(84, 96), mr=(14, 18), mt=8, mb=36)
    s['X'] = dict(lo=0.0, hi=1.0, ticks=[[v, '%d%%' % round(100 * v)] for v in (0.0, 0.25, 0.5, 0.75, 1.0)],
                  title='share of reviews', ntitle='share')
    ticks, e = [], s['els']
    for k, key in enumerate(order):
        top = n - 3 * k
        e.append(dict(t='txt', x=0.0, y=top - 0.45, s=names[key], al='left', bl='middle', c='ink', b=True))
        for r, kind in ((1, 'better'), (2, 'worse')):
            y = top - r - 0.5
            ticks.append([y, '%s design' % kind])
            x0 = 0.0
            for v, (_, col) in zip(data[(key, kind)][:3] + [data[(key, kind)][3]], stages + [('adopted', 'b' if kind == 'better' else 'a')]):
                if v > 0:
                    e.append(dict(t='rect', x0=x0, x1=x0 + v, y0=y - 0.36, y1=y + 0.36, c=col, al=0.85 if col in 'ab' else 0.55))
                    if v >= 0.08:
                        e.append(dict(t='txt', x=x0 + v / 2, y=y, s=pc(v), al='center', bl='middle', c='ink'))
                x0 += v
    s['Y'] = dict(lo=0.0, hi=n + 1.2, ticks=ticks, title='')
    key_items = stages + [('adopted', 'b')]
    for idx, (lab, col) in enumerate(key_items):
        x = (0.0, 0.25, 0.49, 0.72)[idx]
        e += [dict(t='rect', x0=x, x1=x + 0.025, y0=n + 0.55, y1=n + 0.95, c=col, al=0.85 if col == 'b' else 0.55),
              dict(t='txt', x=x + 0.03, y=n + 0.75, s=lab if lab != 'adopted' else 'adopted (red: worse)',
                   n=lab.split()[-1], al='left', bl='middle', c='sub')]
    aria = ('Where reviews of a better and a worse design end, in four settings. ' + ' '.join(
        '%s, %s design: stopped in the team review %s, lost in the hand-off %s, stopped at the approvals %s, adopted %s.'
        % ((names[key], kind) + tuple(pc(v) for v in data[(key, kind)])) for key in order for kind in ('better', 'worse')))
    apart = data[('groups decide apart', 'better')]
    cap = ("Where designs die. Each bar is all the reviews of one design: grey is where the team review stopped it, orange "
           "the managers' hand-off, purple the approvals, and the end of the bar is adoption. Most failures end in the team "
           "review, not at the approvals: with groups deciding apart, %s of reviews of a better design stop there. The "
           "approvals stop a design only when the status quo sits among their priorities, and then they stop every one, "
           "better or worse." % pc(apart[0]))
    FIGS.append(Figure('lifecycle', s, aria, cap))


def fig_upgrade():
    """Part 2: four measured tiers of models, how often one model and a large panel of them are wrong, and how alike
    their mistakes are (T12)."""
    tiers = []
    for r in section('T12'):
        c = cells(r)
        if c[0].startswith('tier '):
            assert c[3].startswith('mean error') and c[4].startswith('latent rho') and c[7].startswith('floor'), c
            tiers.append([float(c[3].split()[-1]), float(c[4].split()[-1]), float(c[7].split()[-1])])
    assert all(b[0] < a[0] and b[2] < a[2] for a, b in zip(tiers, tiers[1:])), 'every measured upgrade lowers both'

    def pc(v):
        return '%.0f%%' % (100 * v)
    xs = [1, 2, 3, 4]
    s = base('chart-upgrade', 320, ml=(40, 48), mr=(120, 170))
    s['X'] = dict(lo=0.7, hi=4.3, ticks=[[1, 'weakest'], [2, '2nd'], [3, '3rd'], [4, 'strongest']],
                  title='tier of measured models, by accuracy', ntitle='tier')
    s['Y'] = dict(lo=0.0, hi=0.5, ticks=[[v, '%d%%' % round(100 * v)] for v in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)],
                  title='questions answered wrong', ntitle='wrong')
    e = s['els']
    e.append(dict(t='band', pts=[[x, t[2], t[0]] for x, t in zip(xs, tiers)], c='b', al=0.12))
    e.append(dict(t='line', pts=[[x, t[0]] for x, t in zip(xs, tiers)], c='g', w=2.5, mk=3.5))
    e.append(dict(t='line', pts=[[x, t[2]] for x, t in zip(xs, tiers)], c='b', w=2.5, mk=3.5))
    e.append(dict(t='txt', x=4, y=tiers[-1][0], s='one model', al='left', bl='bottom', dx=8, dy=-2, c='g', b=True))
    e.append(dict(t='txt', x=4, y=tiers[-1][2], s='a large panel of them', n='large panel', al='left', bl='top', dx=8, dy=2,
                  c='b', b=True))
    for x, t in zip(xs, tiers):
        e.append(dict(t='txt', x=x, y=t[0], s='mistakes alike: %.2f' % t[1], n='%.2f' % t[1], al='center', bl='bottom',
                      dy=-10, c='sub'))
    aria = ('For four tiers of measured models, weakest to strongest: how often one model is wrong, %s; how often a large '
            'panel of them is wrong, %s; and how alike their mistakes are, a latent correlation of %s.' % (
                ', '.join(pc(t[0]) for t in tiers), ', '.join(pc(t[2]) for t in tiers),
                ', '.join('%.2f' % t[1] for t in tiers)))
    cap = ('Where an upgrade takes a panel. Stronger models are wrong less often, and so is a large panel of them: every '
           'measured upgrade lowered both. The shaded gap is all that voting buys, and it stays thin, because the models\' '
           'mistakes grow more alike as they improve, from %.2f to %.2f. A large panel of the strongest tier is wrong on '
           '%s of questions, one of its models on %s.' % (tiers[0][1], tiers[-1][1], pc(tiers[-1][2]), pc(tiers[-1][0])))
    FIGS.append(Figure('upgrade', s, aria, cap))


def fig_reading():
    """Part 3: how often a model uses the decisive fact, read whole or in parts, for local and relational facts (T29)."""
    rows = {}
    for r in section('T29'):
        c = cells(r)
        if c[0] == 'depth 0.3':
            rows[(c[1].split()[0], c[2].split()[1])] = [number(v) for v in c[4:8]]
    xs = [1, 2, 3, 4]
    s = base('chart-reading', 320, ml=(40, 48), mr=(110, 170))
    s['X'] = dict(lo=0.7, hi=4.3, ticks=[[1, 'whole'], [2, '2 parts'], [3, '4 parts'], [4, '8 parts']],
                  title='how the document is read, each part in its own call', ntitle='read in')
    s['Y'] = dict(lo=0.0, hi=1.0, ticks=[[0.0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1.0, '100%']],
                  title='chance the model uses the decisive fact', ntitle='fact used')
    e = s['els']
    loc, rel = rows[('local', '1.00')], rows[('relational', '1.00')]
    assert loc[3] > loc[0] and rel[3] < rel[0]
    e.append(dict(t='line', pts=[[x, y] for x, y in zip(xs, loc)], c='b', w=2.5, mk=3.5))
    e.append(dict(t='line', pts=[[x, y] for x, y in zip(xs, rel)], c='a', w=2.5, mk=3.5))
    e.append(dict(t='txt', x=4, y=loc[3], s='a fact in one place', n='one place', al='left', bl='middle', dx=8, c='b', b=True))
    e.append(dict(t='txt', x=4, y=rel[3], s='a fact across two passages', n='two passages', al='left', bl='middle', dx=8,
                  c='a', b=True))
    aria = ('The chance a model uses the decisive fact of a design document that fills its context window, read whole or '
            'in 2, 4 or 8 overlapping parts. A fact in one place: %s. A fact that needs two distant passages: %s.' % (
                ', '.join('%.0f%%' % (100 * v) for v in loc), ', '.join('%.0f%%' % (100 * v) for v in rel)))
    cap = ('Split the reading, not the design. Read in more parts, a model uses a fact in one place more often, %.0f%% '
           'whole and %.0f%% in eight parts, and a fact that spans two distant passages less often, %.0f%% and %.0f%%, '
           'because the two passages rarely land in the same part. The same holds at every document length and recall '
           'curve tried.' % (100 * loc[0], 100 * loc[3], 100 * rel[0], 100 * rel[3]))
    FIGS.append(Figure('reading', s, aria, cap))


def fig_region():
    """Part 3: every combination of instruments on the two numbers of the series (T34)."""
    pts = []
    for r in section('T34'):
        c = cells(r)
        if c[0] != 'region' or c[1] != 'pilot team first':
            continue
        reading, combining, debate, critic = c[2].split(' + ')
        stage = 3 if critic != 'no critic' else 2 if reading != 'no reading' else 1 if debate != 'no debate' else 0
        pts.append([c[2], number(c[3].split()[-1]), number(c[4].split()[-1]), stage])
    def widest(k):
        ix = [i for i, p in enumerate(pts) if p[3] <= k]
        return max(ix, key=lambda i: pts[i][1] - pts[i][2])
    marks = [widest(k) for k in range(4)]
    best = pts[marks[3]]
    assert 'verified critic' in best[0] and 'debate first' in best[0]
    def pc(v):
        return '%.0f%%' % (100 * v)
    table = {p[0]: (p[1], p[2]) for p in pts}

    def combo(reading='no reading', rule='groups apart', debate='no debate', critic='no critic'):
        return table[' + '.join((reading, rule, debate, critic))]
    order = [('The meeting alone', combo()),
             ('Agreement mediator', combo(rule='agreement mediator')),
             ('Pooled by reliability', combo(rule='pooled by reliability')),
             ('Debate heard first', combo(debate='debate first')),
             ('Debate heard after', combo(debate='debate after')),
             ('Model reads in parts', combo(reading='reading in parts')),
             ('Verified critic', combo(critic='verified critic')),
             ('Contrarian critic', combo(critic='contrarian critic')),
             ('Reader, debate and critic', (best[1], best[2]))]
    alone = order[0][1]
    n = len(order)
    s = base('chart-region', 60 + 30 * n, ml=(150, 168), mr=(14, 18), mt=8, mb=36)
    s['X'] = dict(lo=0.0, hi=1.0, ticks=[[v, '%d%%' % round(100 * v)] for v in (0.0, 0.25, 0.5, 0.75, 1.0)],
                  title='share of reviews that adopt the design', ntitle='share adopted')
    s['Y'] = dict(lo=-0.6, hi=n + 0.6, ticks=[[n - 1 - i, lab] for i, (lab, _) in enumerate(order)], title='')
    e = s['els']
    e += [dict(t='line', pts=[[alone[0], -0.5], [alone[0], n - 0.5]], c='b', w=1, dash=True),
          dict(t='line', pts=[[alone[1], -0.5], [alone[1], n - 0.5]], c='a', w=1, dash=True),
          dict(t='pt', x=0.02, y=n + 0.2, r=4, c='b'),
          dict(t='txt', x=0.02, y=n + 0.2, s='a better design adopted', n='better adopted', al='left', bl='middle', dx=8, c='b'),
          dict(t='pt', x=0.4, y=n + 0.2, r=4, c='a'),
          dict(t='txt', x=0.4, y=n + 0.2, s='a worse design adopted', n='worse adopted', al='left', bl='middle', dx=8, c='a'),
          dict(t='txt', x=0.98, y=n + 0.2, s='dotted: the meeting alone', n='dotted: alone', al='right', bl='middle', c='sub')]
    for i, (lab, (g, bd)) in enumerate(order):
        y = n - 1 - i
        if g == 0 and bd == 0:
            e += [dict(t='pt', x=0.0, y=y, r=5, c='g'),
                  dict(t='txt', x=0.0, y=y, s='blocks everything, better or worse', n='blocks everything', al='left',
                       bl='middle', dx=10, c='sub', b=True)]
            continue
        e += [dict(t='line', pts=[[bd, y], [g, y]], c='g', w=3),
              dict(t='pt', x=bd, y=y, r=5, c='a'), dict(t='pt', x=g, y=y, r=5, c='b'),
              dict(t='txt', x=g, y=y, s='%d%%' % round(100 * g), al='left', bl='middle', dx=8, c='b', b=True),
              dict(t='txt', x=bd, y=y, s='%d%%' % round(100 * bd), al='right', bl='middle', dx=-8, c='a')]
    aria = ('How often the running review adopts a better and a worse design with each instrument, and with the best '
            'combination. ' + ' '.join('%s: better %d%%, worse %d%%.' % (lab, round(100 * g), round(100 * bd))
                                       for lab, (g, bd) in order))
    cap = ('What each instrument buys. Blue is how often the review adopts a better design, red how often a worse one, and '
           'the dotted lines mark the meeting alone, %s and %s. Most instruments move both dots: a verified critic lifts '
           'better designs to %s but lets worse ones through %s of the time, and a contrarian critic blocks everything. '
           'Together, a model reading in parts, a debate heard first and a verified critic reach %s against %s.'
           % (pc(alone[0]), pc(alone[1]), pc(combo(critic='verified critic')[0]), pc(combo(critic='verified critic')[1]),
              pc(best[1]), pc(best[2])))
    FIGS.append(Figure('region', s, aria, cap))


def fig_instruments():
    """Part 3: adoption as instruments are added one at a time, for each way the groups combine (T34)."""
    pts = {}
    for r in section('T34'):
        c = cells(r)
        if c[0] == 'region' and c[1] == 'pilot team first':
            pts[c[2]] = (number(c[3].split()[-1]), number(c[4].split()[-1]))
    rules = ['groups apart', 'agreement mediator', 'pooled by reliability']
    path = [('no reading', 'no debate', 'no critic'), ('no reading', 'debate first', 'no critic'),
            ('reading in parts', 'debate first', 'no critic'), ('reading in parts', 'debate first', 'verified critic')]
    stages = [[list(pts[' + '.join((r, rule, d, c))]) for rule in rules] for r, d, c in path]
    s0, s1, s2, s3 = stages
    spread = [max(v[0] for v in st) - min(v[0] for v in st) for st in stages]
    assert spread[0] > spread[1] > spread[2] > spread[3], 'the combining rules converge as instruments are added'

    def pc(v):
        return '%.0f%%' % (100 * v)

    def span(k, m):
        lo, hi = min(v[m] for v in stages[k]), max(v[m] for v in stages[k])
        return pc(lo) if pc(lo) == pc(hi) else '%s to %s' % (pc(lo), pc(hi))
    s = base('chart-instruments', 320, ml=(40, 46), mr=(16, 24))
    s['X'] = dict(lo=0.0, hi=3.0, ticks=[[0, 'meeting alone'], [1, '+ debate'], [2, '+ reader'], [3, '+ verified critic']],
                  title='instruments heard before the vote, added one at a time', ntitle='instruments added')
    s['Y'] = dict(lo=0.0, hi=1.0, ticks=[[0.0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1.0, '100%']],
                  title='designs adopted', ntitle='adopted')
    for j, col in enumerate(('g', 'd', 'b')):
        s['els'].append(dict(t='line', pts=[[k, stages[k][j][1]] for k in range(4)], c='a', w=1, mk=2, dash=True))
        s['els'].append(dict(t='line', pts=[[k, stages[k][j][0]] for k in range(4)], c=col, w=2.5, mk=3.5))
    for j, (name, col, dy) in enumerate((('apart', 'g', 12), ('agreement', 'd', -12), ('reliability', 'b', -12))):
        s['els'].append(dict(t='txt', x=0, y=s0[j][0], s=name, al='left', bl='middle', dx=8, dy=dy, c=col, b=True))
    s['els'].append(dict(t='txt', x=3, y=max(v[0] for v in s3), s='better designs: the three rules meet', n='better: rules meet', al='right', bl='bottom', dy=-8, c='ink'))
    s['els'].append(dict(t='txt', x=0, y=max(v[1] for v in s0), s='worse designs, all three rules (red, dashed)', n='worse, dashed',
                         al='left', bl='bottom', dx=8, dy=-10, c='a'))
    aria = ('How often a better and a worse design are adopted as instruments heard before the vote are added one at a '
            'time, for each of three ways the groups combine their views. Meeting alone: better designs %s, %s and %s; '
            'worse %s, %s and %s. With a debate heard first, better %s and worse %s; with a reader added, better %s and '
            'worse %s; with a verified critic, better %s and worse %s.' % (
                pc(s0[0][0]), pc(s0[1][0]), pc(s0[2][0]), pc(s0[0][1]), pc(s0[1][1]), pc(s0[2][1]), span(1, 0), span(1, 1),
                span(2, 0), span(2, 1), span(3, 0), span(3, 1)))
    cap = ('Instruments take over the meeting, one group at a time. Without instruments, how the groups combine their views '
           'moves adoption of a better design from %s to %s. A debate heard first outweighs the two weaker groups but not the '
           'pilot team, so the rules still differ, %s. The reader and the verified critic add evidence until it outweighs '
           'every member, and the three rules converge on %s better against %s worse.' % (
               pc(min(v[0] for v in s0)), pc(max(v[0] for v in s0)), span(1, 0), span(3, 0), span(3, 1)))
    FIGS.append(Figure('instruments', s, aria, cap))


def fig_capture():
    """Part 3, Proposition 7: what an AI verdict heard first does to the review, zone by zone along its accuracy,
    against answers recorded first (T37)."""
    n, p, rho = 15, 0.30, 0.25
    row = [cells(r) for r in section('T37') if r.strip()[:4] == '%.2f' % p and number(cells(r)[1]) == rho][0]
    pmaj = number(row[3])
    q = 1 - p
    room = 1 - pmaj

    def pc(v):
        return '%.1f%%' % (100 * v) if round(100 * v, 1) != round(100 * v) else '%.0f%%' % (100 * v)
    s = base('chart-capture', 230, ml=(10, 14), mr=(10, 14), mt=10, mb=42)
    s['X'] = dict(lo=0.5, hi=1.0, ticks=[[0.5, '50%'], [0.6, '60%'], [0.7, '70%'], [0.8, '80%'], [0.9, '90%'],
                                       [1.0, '100%']], title='how often the AI verdict is right', ntitle='AI right')
    s['Y'] = dict(lo=0.0, hi=2.4, ticks=[], title='', ntitle='')
    s['els'] += [dict(t='rect', x0=0.5, x1=q, y0=1.1, y1=1.7, c='g', al=0.15),
                 dict(t='rect', x0=q, x1=room, y0=1.1, y1=1.7, c='a', al=0.25),
                 dict(t='rect', x0=room, x1=1.0, y0=1.1, y1=1.7, c='b', al=0.18),
                 dict(t='rect', x0=0.5, x1=1.0, y0=0.1, y1=0.7, c='g', al=0.15),
                 dict(t='line', pts=[[q, 1.1], [q, 2.4]], c='sub', w=1, dash=True),
                 dict(t='line', pts=[[room, 1.1], [room, 2.4]], c='sub', w=1, dash=True),
                 dict(t='txt', x=q, y=2.25, s='one reviewer: %s' % pc(q), n=pc(q), al='right', bl='middle', dx=-5, c='sub'),
                 dict(t='txt', x=room, y=2.25, s='the room alone: %s' % pc(room), n=pc(room), al='left', bl='middle', dx=5,
                      c='sub'),
                 dict(t='txt', x=0.5, y=1.9, s='AI heard first', al='left', bl='middle', dx=2, b=True),
                 dict(t='txt', x=0.5, y=0.9, s='Answers recorded first', al='left', bl='middle', dx=2, b=True),
                 dict(t='txt', x=(0.5 + q) / 2, y=1.4, s='ignored: right %s' % pc(room), n='ignored', al='center',
                      bl='middle', c='ink'),
                 dict(t='txt', x=(q + room) / 2, y=1.4, s='copied: worse', n='worse', al='center', bl='middle', c='a',
                      b=True),
                 dict(t='txt', x=(room + 1.0) / 2, y=1.4, s='copied: as good as the AI', n='= AI', al='center',
                      bl='middle', c='b', b=True),
                 dict(t='txt', x=0.75, y=0.4, s='nothing to copy: the room decides, right %s' % pc(room), n='right %s' % pc(room),
                      al='center', bl='middle', c='ink')]
    aria = ('How often a review of %d members, each right %s of the time with errors correlated at %s, is right, '
            'against how often an AI verdict is right. Heard first, the verdict is ignored up to %s, where the review is '
            'right %s of the time; above it every member follows the verdict and the review is right exactly as often as '
            'the verdict, which is worse than the room between %s and %s. With answers recorded first the review stays at '
            '%s whatever the verdict.' % (n, pc(q), rho, pc(q), pc(room), pc(q), pc(room), pc(room)))
    cap = ('Who speaks first (Proposition 7). Heard first, an AI verdict is ignored until it is surer than one reviewer, '
           'then everyone copies it, and the review becomes exactly as good as the AI: worse than the room between %s and '
           '%s, better above. With answers recorded first, the room keeps its %s whatever the AI.' % (pc(q), pc(room),
                                                                                                   pc(room)))
    FIGS.append(Figure('capture', s, aria, cap))


def fig_energy():
    """Part 3, Proposition 8: disagreements each kind of review must settle against what a quarter holds, and how
    often it decides right, by number of pieces (T39, T41). The post draws the grid key as a table; the
    repository draws the same table from the elements."""
    pieces = (1, 2, 4, 8)
    rows = {}
    for r in section('T41'):
        c = cells(r)
        if len(c) == 6:
            rows[(c[0], int(c[1]))] = dict(plus=number(c[2]), minus=number(c[3]), settle=number(c[4]),
                                           weeks=number(c[5]))
    meet = {p: rows[('meeting', p)] for p in pieces}
    fact = {p: rows[('protocol, 2 holders of the fact', p)] for p in pieces}
    const = [cells(r) for r in section('T39') if cells(r)[0] == 'constants'][0]
    k = {c.split()[0]: number(c.split()[-1]) for c in const[1:]}
    window = k['window']

    def right(v):
        """How often the review decides right when half the designs it sees are better: it adopts the better ones
        and rejects the worse ones."""
        return (v['plus'] + 1.0 - v['minus']) / 2.0

    def pc(v):
        return '%.0f%%' % (100 * v)
    fits = int(round(window / k['settlement']))
    names = {1: 'Whole design', 2: '2 pieces', 4: '4 pieces', 8: '8 pieces'}
    nrows = len(pieces) + 1.5
    s = table('chart-energy', 400, nrows)
    s['grid'] = dict(window=window, fits=fits,
                     rows=[dict(label=names[p],
                                meeting=dict(right=round(right(meet[p]), 4), settle=meet[p]['settle']),
                                protocol=dict(right=round(right(fact[p]), 4), settle=fact[p]['settle']))
                           for p in pieces])
    top = nrows
    s['els'] += [dict(t='txt', x=18, y=top - 0.35, s='The meeting', b=True, bl='middle'),
                 dict(t='txt', x=18, y=top - 0.7, s='everyone settles with everyone', c='sub', bl='middle'),
                 dict(t='txt', x=59, y=top - 0.35, s='The Residual Protocol', b=True, bl='middle'),
                 dict(t='txt', x=59, y=top - 0.7, s='two people who hold the fact', c='sub', bl='middle')]
    step, size, per_row = 1.0, 0.72, 26
    for r, p in enumerate(pieces, start=1):
        y = top - r
        rule(s, y)
        s['els'].append(dict(t='txt', x=1, y=y - 0.45, s=names[p], c='sub', bl='middle'))
        for x0, v in ((18, meet[p]), (59, fact[p])):
            ok, n = right(v), v['settle']
            coin, over = ok < 0.55, n > fits
            s['els'].append(dict(t='txt', x=x0, y=y - 0.2, s='%s right%s' % (pc(ok), ', a coin flip' if coin else ''),
                                 c='g' if coin else 'b', b=True, bl='middle'))
            filled = min(fits, int(round(n)))
            for d in range(fits):
                cx, cy = x0 + (d % per_row) * step, y - 0.38 - (d // per_row) * 0.12
                s['els'].append(dict(t='rect', x0=cx, x1=cx + size, y0=cy, y1=cy - 0.08,
                                     c=('a' if over else 'b') if d < filled else 'grid'))
            text = 'under 1 disagreement' if n < 1 else '%d disagreement%s' % (round(n), '' if round(n) == 1 else 's')
            if over:
                text += ', %d more than a quarter holds' % round(n - fits)
            s['els'].append(dict(t='txt', x=x0, y=y - 0.78, s=text, c='a' if over else 'sub', b=over, bl='middle'))
    rule(s, 0.5)
    s['els'].append(dict(t='txt', x=1, y=0.25, s='Right: correct decisions, half the designs better. Box: one quarter, %d disagreements.' % fits, c='sub', bl='middle'))
    aria = ('How often a review decides right, with half the designs better, and how many disagreements people must '
            'settle, as the design is split into 1, 2, 4 or 8 pieces; a %.0f-week quarter fits %d. The meeting: %s, %s, %s '
            'and %s right, with %.0f, %.0f, %.0f and %.0f disagreements. The Residual Protocol: %s, %s, %s and %s right, '
            'with at most %.1f.' % tuple([window, fits] + [pc(right(meet[p])) for p in pieces]
                                         + [meet[p]['settle'] for p in pieces]
                                         + [pc(right(fact[p])) for p in pieces] + [fact[8]['settle']]))
    cap = ('What the review costs (Proposition 8). Each dot is a disagreement someone must settle, and each box holds '
           'one quarter. Split a design, and the meeting must settle every pair of opinions until it overflows the '
           'quarter and stalls at a coin flip. The Residual Protocol asks only the people who hold the facts: a dot or '
           'two, and it stays right.')
    FIGS.append(Figure('energy', s, aria, cap))


BUILDERS = [fig_frontier, fig_correlation, fig_lifecycle, fig_upgrade, fig_reading, fig_region, fig_instruments, fig_capture,
            fig_energy]


def figures(results_path):
    """Build every figure from the results file at results_path, in a fixed order."""
    RESULTS.clear()
    RESULTS.update(read(results_path))
    FIGS.clear()
    for build in BUILDERS:
        build()
    return list(FIGS)
