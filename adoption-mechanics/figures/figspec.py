"""Figure specifications for Adoption Mechanics, built from the frozen results.

Every plotted number is parsed from the results file, so a figure cannot drift from the executed code. A
specification is a plain dict (id, height, margins, axes X, Y and optional R, and a list of elements); the
shared canvas engine draws it for the posts and tools/svg.py for the repository.

  figures(results_path) -> list of Figure(name, spec, aria, caption)
"""
import math
from statistics import NormalDist

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


LEVER_NAMES = {'pilot': 'reversible pilot', 'gate': 'one exterior gate removed', 'poll': 'blind poll',
               'champion': 'insured champion speaks first', 'decorrelate': 'decorrelated panel', 'layers': 'flatter chain'}


def fig_frontier():
    rows = [cells(r) for r in section('T18')]
    hull = [r for r in rows if r[0].startswith('status quo inside the hull')][0]
    combos = [(r[0], number(r[1]), number(r[2]), r[4] == 'frontier') for r in rows if not r[0].startswith('status quo inside')]
    named = {n: (g, b, f) for n, g, b, f in combos}
    singles = sorted((n for n in named if n in LEVER_NAMES), key=lambda n: -(named[n][0] - named[n][1]))
    multi = sorted((n for n in named if '+' in n and named[n][2]), key=lambda n: -(named[n][0] - named[n][1]))[:5]
    assert all('decorrelate' in n for n in multi)
    assert max(singles, key=lambda n: named[n][1]) == 'champion'
    sections_ = [('today', ['baseline']), ('one lever at a time', singles), ('the widest gaps', multi)]
    lines = []
    for head, names in sections_:
        if head != 'today':
            lines.append(('head', head))
        for n in names:
            lines.append(('row', n))
    s = base('chart-frontier', 46 + 30 * len(lines) + 30, ml=(10, 12), mr=(12, 16), mt=8, mb=36)
    top = len(lines)
    s['X'] = dict(lo=-0.02, hi=1.02, ticks=[[v, '%d%%' % round(100 * v)] for v in (0.0, 0.25, 0.5, 0.75, 1.0)],
                  title='share of reviews that adopt the design', ntitle='share adopted')
    s['Y'] = dict(lo=-0.6, hi=top + 0.7, ticks=[], title='')
    e = s['els']
    e.append(dict(t='txt', x=0.0, y=top + 0.45, s='blue: a better design adopted; grey: a worse one; the line between them is the gap',
                  n='blue: better adopted; grey: worse', al='left', bl='middle', c='sub'))
    for i, (kind, n) in enumerate(lines):
        y = top - 1 - i
        if kind == 'head':
            e.append(dict(t='txt', x=0.0, y=y + 0.05, s=n, n=n, al='left', bl='middle', c='ink', b=True))
            continue
        g, bd, _ = named[n]
        label = ('today: no lever' if n == 'baseline' else 'all six levers' if n.count('+') == 5
                 else ' + '.join(LEVER_NAMES[k] for k in n.split('+')))
        nlabel = 'today' if n == 'baseline' else 'all six' if n.count('+') == 5 else ' + '.join(n.split('+'))
        e.append(dict(t='txt', x=0.0, y=y + 0.28, s=label, n=nlabel, al='left', bl='middle', c='a' if n == 'baseline' else 'ink'))
        e.append(dict(t='line', pts=[[bd, y - 0.12], [g, y - 0.12]], c='g', w=3))
        e.append(dict(t='pt', x=bd, y=y - 0.12, r=5, c='g'))
        e.append(dict(t='pt', x=g, y=y - 0.12, r=5, c='b'))
        e.append(dict(t='txt', x=g, y=y - 0.12, s='%d%%' % round(100 * g), n='%d%%' % round(100 * g), al='left', bl='middle', dx=8, c='b', b=True))
        e.append(dict(t='txt', x=bd, y=y - 0.12, s='%d%%' % round(100 * bd), n='%d%%' % round(100 * bd), al='right', bl='middle', dx=-8, c='g'))
    base_g, base_b, _ = named['baseline']
    six = 'pilot+gate+poll+champion+decorrelate+layers'
    aria = ('For today\'s review and each choice of levers, how often a better design and a worse design are adopted. ' +
            ' '.join('%s: better %.3f, worse %.3f.' % ('Today' if n == 'baseline' else ' + '.join(LEVER_NAMES[k] for k in n.split('+')),
                                                      named[n][0], named[n][1]) for k_, n in lines if k_ == 'row') +
            ' With the status quo inside the approvers\' hull every choice adopts neither: %.3f, %.3f.' % (number(hull[1]), number(hull[2])))
    cap = ("What each choice buys. Today's review adopts a better design in %d%% of reviews and a worse one in %d%%. Each "
           "lever alone moves both, and the insured champion speaking first raises the worse design's chances most. The widest gaps "
           "all include the decorrelated panel, and all six levers together keep a better design near %d%% while cutting a "
           "worse one to %d%%. With the status quo inside the approvers' hull, no choice adopts either design."
           % (round(100 * base_g), round(100 * base_b), round(100 * named[six][0]), round(100 * named[six][1])))
    FIGS.append(Figure('frontier', s, aria, cap))


def fig_correlation():
    series = {'MMLU': [cells(r) for r in section('T13') if not r.strip().startswith('5 strata')]}
    for r in section('T19'):
        c = cells(r)
        if len(c) > 3:
            series.setdefault(c[0], []).append(c[1:])
    colors = {'MMLU': 'b', 'GPQA': 'a', 'MMLU-Pro': 'c'}
    xs = [1, 2, 3, 4, 5]
    s = base('chart-correlation', 340, ml=(40, 48), mr=(62, 74))
    s['X'] = dict(lo=0.7, hi=5.3, ticks=[[1, 'weakest'], [2, '2nd'], [3, '3rd'], [4, '4th'], [5, 'strongest']],
                  title='fifth of model pairs, by mean accuracy', ntitle='fifth of pairs')
    s['Y'] = dict(lo=0.7, hi=25.0, log=True, ticks=[[1, '1'], [2, '2'], [5, '5'], [10, '10'], [20, '20']],
                  title='odds ratio of a shared mistake (log scale)', ntitle='odds ratio (log)')
    e = s['els']
    e.append(dict(t='hline', y=1.0, c='g', w=1))
    lines = {}
    for name in ('MMLU', 'GPQA', 'MMLU-Pro'):
        rows = series[name]
        pooled = [number(r[4]) for r in rows]
        within = [number(r[5]) for r in rows]
        lines[name] = (pooled, within)
        e.append(dict(t='line', pts=[[x, v] for x, v in zip(xs, pooled)], c=colors[name], w=2, mk=3))
        e.append(dict(t='line', pts=[[x, v] for x, v in zip(xs, within)], c=colors[name], w=1.5, dash=True, mk=3))
        e.append(dict(t='txt', x=5, y=pooled[-1], s=name, n=name, al='left', bl='middle', dx=8, c=colors[name], b=True))
    e.append(dict(t='txt', x=0.85, y=21.0, s='solid: all questions; dashed: questions of similar difficulty', n='solid: all; dashed: same difficulty', al='left', bl='middle', c='g'))
    aria = ('Odds ratio that two language models make the same mistake, by fifth of model pairs ordered by mean accuracy, '
            'on three benchmarks from Stanford HELM. ' + ' '.join(
                '%s, all questions: %s; questions of similar difficulty: %s.' % (
                    n, ', '.join('%.2f' % v for v in lines[n][0]), ', '.join('%.2f' % v for v in lines[n][1]))
                for n in ('MMLU', 'GPQA', 'MMLU-Pro')))
    cap = ('What stronger models share. Over all questions, the odds that two models make the same mistake rise with their '
           'accuracy on all three benchmarks, to %.0f, %.0f and %.0f for the strongest fifth of pairs. Among questions of '
           'similar difficulty the odds ratio stays near 1 for most pairs: shared difficulty explains most of it. The '
           'strongest fifth keep a residual, %.2f, %.2f and %.2f: the best models also share blind spots of their own.'
           % (lines['MMLU'][0][-1], lines['GPQA'][0][-1], lines['MMLU-Pro'][0][-1],
              lines['MMLU'][1][-1], lines['GPQA'][1][-1], lines['MMLU-Pro'][1][-1]))
    FIGS.append(Figure('correlation', s, aria, cap))


def _after_label(cell):
    """The value of a results cell such as 'acts ++-/+++': everything after the first word."""
    return cell.split(' ', 1)[1]


def _counts100(f):
    """The four fates of 100 reviews as whole numbers that sum to 100 (largest remainder), as the post draws them."""
    keys = ['review', 'handoff', 'approvals', 'adopted']
    raw = [100 * f[k] for k in keys]
    out = [math.floor(v) for v in raw]
    for i in sorted(range(4), key=lambda i: -(raw[i] - out[i]))[:100 - sum(out)]:
        out[i] += 1
    return out


def fig_lifecycle():
    steps = []
    for r in section('T26'):
        c = cells(r)
        if c[0].startswith('groups decide apart, evidence'):
            continue
        assert c[2].startswith('dies in review') and c[5].startswith('adopted'), c
        rec = dict(review=float(c[2].split()[-1]), handoff=float(c[3].split()[-1]), approvals=float(c[4].split()[-1]),
                   adopted=float(c[5].split()[-1]))
        if not steps or steps[-1]['name'] != c[0]:
            steps.append(dict(name=c[0]))
        steps[-1]['better' if c[1].startswith('better') else 'worse'] = rec
    assert len(steps) == 4 and all('better' in st and 'worse' in st for st in steps)
    bins = ['stopped in the team review', 'lost in the hand-off', 'stopped at the approvals', 'adopted']
    s = base('anim-lifecycle', 330, ml=(8, 10), mr=(8, 10), mt=8, mb=8)
    s['X'] = dict(lo=0.0, hi=4.0, ticks=[], title='')
    s['Y'] = dict(lo=0.0, hi=26.0, ticks=[], title='')
    e = s['els']
    for b, name in enumerate(bins):
        e.append(dict(t='rect', x0=b + 0.03, x1=b + 0.97, y0=0.2, y1=25.8, c='c' if b == 3 else 'g', al=0.08))
        e.append(dict(t='txt', x=b + 0.06, y=25.2, s=name, n=name, al='left', bl='middle', c='ink', b=b == 3))
    replay = []
    code = {'review': 'r', 'handoff': 'h', 'approvals': 'a', 'adopted': 'd'}
    for r in section('T28'):
        c = cells(r)
        if c[0] == 'setting':
            replay.append(dict(name=c[1], champion=c[2] == 'champion speaks first', threshold=float(c[3].split()[-1]),
                               apart='/' in '', better=[], worse=[]))
        elif c[0] == 'trace':
            st = replay[-1]
            assert st['name'] == c[1]
            st['apart'] = '/' in _after_label(c[4])
            st[c[2]].append(';'.join([_after_label(c[4]), _after_label(c[5]), _after_label(c[6]).replace(' ', ','), _after_label(c[8]).replace(' ', ','),
                                      _after_label(c[9]).replace(' ', ','), _after_label(c[10]).replace(' ', ','), code[c[11]]]))
    assert [st['name'] for st in replay] == [st['name'] for st in steps]
    assert all(len(st['better']) == 100 and len(st['worse']) == 100 for st in replay)
    for st, rp in zip(steps, replay):
        rp['share'] = dict(better=st['better'], worse=st['worse'])
    order = ['r', 'h', 'a', 'd']
    for kind, col, top in (('better', 'b', 23.0), ('worse', 'g', 11.0)):
        c = [sum(t.endswith(';' + k) for t in replay[0][kind]) for k in order]
        e.append(dict(t='txt', x=0.06, y=top + 0.6, s='100 reviews of a %s design: %s' % (kind, replay[0]['name']), n=kind, al='left', bl='middle', c=col))
        for b in range(4):
            for j in range(c[b]):
                e.append(dict(t='pt', x=b + 0.08 + 0.084 * (j % 10) + 0.04, y=top - 0.9 * (j // 10) - 0.4, r=3, c=col))
    s['ix'] = dict(steps=steps, bins=bins, replay=replay)
    aria = ('Where reviews of the same design end, out of 100 reviews of a better and of a worse design: stopped in the team '
            "review, lost in the managers' hand-off, stopped at the approvals, or adopted. " + ' '.join(
                '%s: better design %s; worse design %s.' % (st['name'].capitalize(),
                ', '.join('%d %s' % (n, bn) for n, bn in zip(_counts100(st['better']), bins)),
                ', '.join('%d %s' % (n, bn) for n, bn in zip(_counts100(st['worse']), bins))) for st in steps))
    cap = ("Where designs die. Most reviews that fail end in the team review, not at the approvals; the approvals stop a "
           "design only when the status quo sits among their priorities, and then they stop every one. Each review shown "
           "is one the model ran: the first 100 of 20,000 per setting, replayed vote by vote, with the share over all "
           "20,000 beside them. The groups' sizes and shares of the evidence are illustrative, and site reliability's "
           "release check, after the decision, is not modeled.")
    FIGS.append(Figure('lifecycle', s, aria, cap))


def _floor(p, rho):
    nd = NormalDist()
    return nd.cdf(nd.inv_cdf(p) / math.sqrt(rho))


def fig_upgrade():
    path = []
    for r in section('T11'):
        c = cells(r)
        path.append([number(c[0]), number(c[1]), number(c[2])])
    tiers = []
    for r in section('T12'):
        c = cells(r)
        if c[0].startswith('tier '):
            assert c[3].startswith('mean error') and c[4].startswith('latent rho') and c[7].startswith('floor'), c
            tiers.append([float(c[3].split()[-1]), float(c[4].split()[-1]), float(c[7].split()[-1])])
    levels = [0.02, 0.05, 0.10, 0.20, 0.30, 0.40]
    lo_p, hi_p, lo_r, hi_r = 0.06, 0.5, 0.05, 1.0
    s = base('anim-upgrade', 430, ml=(44, 54), mr=(12, 18), mt=24, mb=42)
    s['X'] = dict(lo=lo_p, hi=hi_p, log=True, ticks=[[v, '%d%%' % round(100 * v)] for v in (0.06, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5)],
                  title="member error p (log scale; an upgrade moves left)", ntitle='member error p')
    s['Y'] = dict(lo=lo_r, hi=hi_r, log=True, ticks=[[v, ('%.2f' % v).rstrip('0').rstrip('.') if v < 1 else '1'] for v in (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0)],
                  title="latent correlation of members' errors (log scale)", ntitle='latent correlation')
    e = s['els']
    nd = NormalDist()
    for L in levels:
        zl = nd.inv_cdf(L)
        pts = []
        for i in range(161):
            p = math.exp(math.log(max(L, lo_p)) + (math.log(0.4999) - math.log(max(L, lo_p))) * i / 160)
            r = min(1.0, (nd.inv_cdf(p) / zl) ** 2)
            if r >= lo_r:
                pts.append([p, r])
        e.append(dict(t='line', pts=pts, c='g', w=1.2))
        top = max(pts, key=lambda q: q[1])
        e.append(dict(t='txt', x=top[0], y=top[1], s='%g%%' % (100 * L), n='%g%%' % (100 * L), al='center', bl='bottom', dy=-2, c='g', b=True))
    for a, b in zip(path, path[1:]):
        e.append(dict(t='line', pts=[a[:2], b[:2]], c='a' if b[2] > a[2] else 'c', w=2.5))
    e.append(dict(t='line', pts=[q[:2] for q in path], c='b', w=0, mk=4))
    e.append(dict(t='txt', x=path[0][0], y=path[0][1], s='constructed path: floor %.1f%%, %.1f%%, %.1f%%, %.1f%%, %.1f%%' % tuple(100 * q[2] for q in path),
                  n='constructed path', al='right', bl='top', dx=-8, dy=6, c='ink'))
    e.append(dict(t='line', pts=[q[:2] for q in tiers], c='c', w=2.5, mk=4))
    e.append(dict(t='txt', x=tiers[0][0], y=tiers[0][1], s='MMLU tiers: floor %d%%, %d%%, %d%%, %d%%' % tuple(round(100 * q[2]) for q in tiers),
                  n='MMLU tiers', al='right', bl='top', dx=-4, dy=10, c='ink'))
    for q in path + tiers:
        assert abs(_floor(q[0], q[1]) - q[2]) < 5e-4, q
    s['ix'] = dict(levels=levels, path=path, tiers=tiers)
    aria = ("Member error against the latent correlation of members' errors, both on log scales, with curves of equal "
            "large-panel floor at %s. An upgrade improves a large panel only if it ends on a lower curve. A constructed "
            "path from %d%% error at correlation %.2f to %d%% at %.2f moves the floor through %s. Four MMLU accuracy "
            "tiers, from %d%% error at correlation %.2f to %d%% at %.2f, move it through %s."
            % (', '.join('%g%%' % (100 * L) for L in levels), round(100 * path[0][0]), path[0][1], round(100 * path[-1][0]),
               path[-1][1], ', '.join('%.1f%%' % (100 * q[2]) for q in path), round(100 * tiers[0][0]), tiers[0][1],
               round(100 * tiers[-1][0]), tiers[-1][1], ', '.join('%d%%' % round(100 * q[2]) for q in tiers)))
    cap = ("Where an upgrade takes a panel. The curves are exact: each joins the members whose large panel errs on the same "
           "share of questions (Proposition 1), and on these log scales a curve's steepness is the critical elasticity of "
           "Corollary 1. The path is constructed to show the effect. Each measured tier is placed at its mean error and mean "
           "pooled correlation, an approximation to the panel it stands for.")
    FIGS.append(Figure('upgrade', s, aria, cap))


def fig_reading():
    rows = {}
    for r in section('T29'):
        c = cells(r)
        if c[0] == 'depth 0.3':
            rows[(c[1].split()[0], c[2].split()[1])] = [number(v) for v in c[4:8]]
    xs = [1, 2, 3, 4]
    s = base('chart-reading', 340, ml=(40, 48), mr=(70, 136))
    s['X'] = dict(lo=0.7, hi=4.3, ticks=[[1, 'whole'], [2, '2 parts'], [3, '4 parts'], [4, '8 parts']],
                  title='how the document is read, each part in its own call', ntitle='read in')
    s['Y'] = dict(lo=0.0, hi=1.0, ticks=[[0.0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1.0, '100%']],
                  title='chance the model uses the decisive fact', ntitle='fact used')
    e = s['els']
    lines = [(('local', '0.25'), 'b', 1.5, True, 'local, quarter window'), (('local', '1.00'), 'b', 2.5, False, 'local, full window'),
             (('relational', '0.25'), 'a', 1.5, True, 'two passages, quarter'), (('relational', '1.00'), 'a', 2.5, False, 'two passages, full')]
    for key, col, w, dash, name in lines:
        v = rows[key]
        e.append(dict(t='line', pts=[[x, y] for x, y in zip(xs, v)], c=col, w=w, dash=dash, mk=3))
    for kind, col, text in (('local', 'b', 'fact in one place'), ('relational', 'a', 'fact in two passages')):
        y = (rows[(kind, '0.25')][3] + rows[(kind, '1.00')][3]) / 2
        e.append(dict(t='txt', x=4, y=y, s=text, n=text.split(' in ')[-1], al='left', bl='middle', dx=8, c=col, b=True))
    e.append(dict(t='txt', x=0.75, y=0.985, s='solid: document fills the whole window; dashed: a quarter of it',
                  n='solid: full window; dashed: quarter', al='left', bl='middle', c='g'))
    assert rows[('local', '1.00')][2] > rows[('local', '1.00')][0] and rows[('relational', '0.25')][3] < rows[('relational', '0.25')][0]
    aria = ('The chance a model uses the decisive fact of a design document, read whole or in 2, 4 or 8 overlapping parts. '
            + ' '.join('%s: %s.' % (name, ', '.join('%.2f' % v for v in rows[key])) for key, _, _, _, name in lines))
    cap = ('Split the reading, not the design. A fact in one place is used more often when the model reads the design in '
           'parts: near a full window, %.0f%% whole and %.0f%% in four parts. A fact that needs two distant passages goes '
           'the other way: at a quarter window, %.0f%% whole and %.0f%% in eight parts, because the two passages rarely land '
           'in the same call. Recall by position follows Definition 5 with a dip of depth 0.3; the direction holds at every '
           'depth swept.' % (100 * rows[('local', '1.00')][0], 100 * rows[('local', '1.00')][2],
                              100 * rows[('relational', '0.25')][0], 100 * rows[('relational', '0.25')][3]))
    FIGS.append(Figure('reading', s, aria, cap))


def fig_region():
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
    start = [p for p in pts if p[0] == 'no reading + groups apart + no debate + no critic'][0]
    agree = [p for p in pts if p[0] == 'no reading + agreement mediator + no debate + no critic'][0]
    best = pts[marks[3]]
    assert 'verified critic' in best[0] and 'debate first' in best[0]
    def pc(v):
        return '%.0f%%' % (100 * v)
    steps = [
        dict(mark=marks[0], label='widest gap', text='Without instruments the meeting has three ways to combine its groups. Deciding apart adopts a better design %s of the time and a worse one %s; an agreement mediator raises the first to %s and the second to %s.' % (pc(start[1]), pc(start[2]), pc(agree[1]), pc(agree[2]))),
        dict(mark=marks[1], label='widest gap', text='A debate between two models, right 75%% of the time, heard before or after the vote. Heard first it captures the panel; the widest gap so far is %s against %s.' % (pc(pts[marks[1]][1]), pc(pts[marks[1]][2]))),
        dict(mark=marks[2], label='widest gap', text='A model reads the design whole or in four parts and reports the decisive local fact when it uses it. The reports are accurate, so heard first they pull every combination upward: %s against %s.' % (pc(pts[marks[2]][1]), pc(pts[marks[2]][2]))),
        dict(mark=marks[3], label='widest gap', text='A critic whose false flags people verify away, or a contrarian one. The verified critic with the debate first and the reading in parts gives the widest gap, %s against %s, and the combining rule barely matters any more.' % (pc(best[1]), pc(best[2])))]
    s = base('anim-region', 380)
    s['ix'] = dict(points=pts, steps=steps, xmax=0.3, xticks=[0.0, 0.1, 0.2, 0.3])
    s['X'] = dict(lo=0.0, hi=0.3, ticks=[[0.0, '0%'], [0.1, '10%'], [0.2, '20%'], [0.3, '30%']],
                  title='worse design adopted', ntitle='worse adopted')
    s['Y'] = dict(lo=0.0, hi=1.0, ticks=[[0.0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1.0, '100%']],
                  title='better design adopted', ntitle='better adopted')
    for p in pts:
        s['els'].append(dict(t='pt', x=min(p[2], 0.3), y=p[1], r=3 if p[3] == 3 else 2.5, c='b' if p[3] == 3 else 'g'))
    s['els'].append(dict(t='txt', x=min(best[2], 0.3), y=best[1], s='widest gap: verified critic, debate first, reading in parts',
                         n='widest gap', al='left', bl='middle', dx=10, dy=12, c='ink', b=True))
    aria = ('Adoption of a better design against adoption of a worse one for every combination of reading, combining rule, '
            'debate and critic in the running review. Without instruments, groups deciding apart: %s and %s. Widest gap: %s, '
            '%s and %s.' % (pc(start[1]), pc(start[2]), best[0], pc(best[1]), pc(best[2])))
    cap = ('The region of instruments. Every combination of four instruments in the running review, plotted on the two numbers '
           'of the series. Without instruments the meeting sits near %s and %s. Each instrument heard first is a shared input, '
           'and accurate shared inputs capture the panel, so the widest gaps come from the instruments themselves: a verified '
           'critic and a debate heard first, with the design read in parts, reach %s against %s. Once they are there, the '
           'meeting\'s own rule for combining views no longer decides the outcome.' % (pc(start[1]), pc(start[2]), pc(best[1]), pc(best[2])))
    FIGS.append(Figure('region', s, aria, cap))


BUILDERS = [fig_frontier, fig_correlation, fig_lifecycle, fig_upgrade, fig_reading, fig_region]


def figures(results_path):
    """Build every figure from the results file at results_path, in a fixed order."""
    RESULTS.clear()
    RESULTS.update(read(results_path))
    FIGS.clear()
    for build in BUILDERS:
        build()
    return list(FIGS)
