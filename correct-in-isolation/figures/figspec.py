"""Figure specifications for Correct in Isolation, built from the frozen results.

Every plotted number is parsed from the results file, so a figure cannot drift from the
executed code. A specification is a plain dict (id, height, margins, axes X, Y and optional R,
and a list of elements: hband, rect, vline, hline, band, line, pt, txt). Two backends draw it:
the shared canvas engine for the posts and tools/svg.py for the repository.

  figures(results_path) -> list of Figure(name, spec, aria, caption)
"""
import math
import re

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


def _n(text):
    """A results cell as the number it prints: an int when it has no decimal point, else a float."""
    text = text.strip()
    return int(text) if re.fullmatch(r'-?\d+', text) else float(text)


def _g(v):
    """A number as the posts write an axis value: 2 rather than 2.0, 1.1 as 1.1."""
    return '%g' % v


def _id_last(s):
    """Move the id to the end, the key order of the specifications first written in the posts."""
    s['id'] = s.pop('id')
    return s


def _axes_first(s):
    """Put the axes before the elements, the key order of the specifications first written in Part 6."""
    els = s.pop('els')
    s['els'] = els
    return s


def _z(v):
    """Zero as the integer the posts write, any other value unchanged."""
    return 0 if v == 0 else v


WORDS = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine'}


def _pct(v):
    return '%d%%' % round(v * 100)


# ---------- Part 1 ----------

def fig_rest_band():
    data = []
    for row in section('T2'):
        c = cells(row)
        lo0, hi0 = (float(x) for x in c[2].split(' to '))
        lo1, hi1 = (float(x) for x in c[4].split(' to '))
        in0 = [] if c[3] == 'none' else [float(x) for x in c[3].split(', ')]
        in1 = [] if c[5] == 'none' else [float(x) for x in c[5].split(', ')]
        data.append((number(c[0]), number(c[1]), lo0, hi0, in0, lo1, hi1, in1))
    s = base('chart-rest-band', 320, ml=(40, 48), mr=(58, 84))
    s['X'] = dict(lo=0.97, hi=1.53, ticks=[[d[0], '%.1f' % d[0]] for d in data],
                  title='q: usage percentile over mean usage per pod', ntitle='q (percentile / mean)')
    s['Y'] = dict(lo=0.44, hi=1.0, ticks=[[v, _pct(v)] for v in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)],
                  title='horizontal target', ntitle='target')
    e = s['els']
    e.append(dict(t='band', pts=[[d[0], d[5], min(d[6], 1.0)] for d in data], c='b', al=0.08))
    e.append(dict(t='band', pts=[[d[0], d[2], d[3]] for d in data], c='b', al=0.2, edge=True))
    e.append(dict(t='line', pts=[[d[0], d[1]] for d in data], c='b', w=1.5, dash=True))
    for target in (0.5, 0.6, 0.7, 0.8, 0.9):
        e.append(dict(t='hline', y=target, c='g', w=1, dash=True))
        e.append(dict(t='txt', x=1.53, y=target, s='%s target' % _pct(target), n=_pct(target), al='left', dx=6, c='sub'))
    for d in data:
        for target in d[7]:
            e.append(dict(t='pt', x=d[0], y=target, r=4, c='c', open=target not in d[4]))
    q0, hi0 = data[0][0], data[0][3]
    e.append(dict(t='txt', x=q0, y=hi0, s='both loops can rest', n='rest band', al='left', bl='bottom', dx=4, dy=-4, c='b', b=True))
    e.append(dict(t='txt', x=q0, y=0.468, s="dashed: the vertical loop's own utilization, 1/((1+m)q)", n='dashed: vertical loop', al='left', c='b'))
    edges = '; '.join('q %.1f: %.3f to %.3f, widened %.3f to %.3f' % (d[0], d[2], d[3], d[5], d[6]) for d in data)
    aria = ('Rest band of horizontal targets against q, margin 0.15 and tolerance 0.1, for a steady load and widened by the vertical autoscaler\'s '
            'documented 10 percent update threshold. %s. Dashed lines mark targets of 50 to 90 percent; filled dots mark targets inside the band '
            'for a steady load, open dots targets inside only the widened band.' % edges)
    cap = ('Which horizontal targets let both loops on one CPU metric rest, against q: the usage percentile the vertical loop sizes '
           'from, over mean usage per pod. Both rest inside the darker band on a steady load; the lighter band is the most the vertical '
           'autoscaler\'s 10% update threshold can add. Filled dots are common targets inside the darker band, open dots only inside '
           'the lighter one. At q = 1, every target of 70% or less is below both. On a strictly steady load the recommender\'s lower bound '
           'sits on its target, so only the lower side of the lighter band applies there.')
    FIGS.append(Figure('rest-band', s, aria, cap))


def fig_drift():
    pts = []
    for row in section('T3'):
        c = cells(row)
        pts.append((number(c[0]) / 24.0, number(c[1]), number(c[4])))
    s = base('chart-drift', 320, ml=(44, 52), mr=(40, 48))
    s['X'] = dict(lo=0, hi=60, ticks=[[d, '%d' % d] for d in (0, 10, 20, 30, 40, 50, 60)], title='days', ntitle='days')
    s['Y'] = dict(lo=6, hi=14000, log=True, ticks=[[10, '10'], [100, '100'], [1000, '1,000'], [10000, '10,000']],
                  title='replicas, log scale', ntitle='replicas (log)', col='a')
    s['R'] = dict(lo=0, hi=260, ticks=[[0, '0'], [100, '100'], [200, '200']], title='requested cores', ntitle='cores', col='b')
    e = s['els']
    e.append(dict(t='line', pts=[[d, n] for d, n, _ in pts], c='a'))
    e.append(dict(t='line', pts=[[d, r] for d, _, r in pts], c='b', ax='R'))
    d0, n0, r0 = pts[0]
    dz, nz, rz = pts[-1]
    first_floor = next(d for d, n, _ in pts if n == nz)
    e.append(dict(t='txt', x=d0, y=n0, s='%d replicas' % n0, al='left', bl='top', dx=6, dy=6, c='a'))
    e.append(dict(t='txt', x=first_floor, y=nz, s='%s replicas at the 25-millicore floor' % format(int(nz), ','),
                  n='%s at the floor' % format(int(nz), ','), al='left', bl='bottom', dx=4, dy=-6, c='a', b=True))
    lo_r, hi_r = min(r for _, _, r in pts), max(r for _, _, r in pts)
    e.append(dict(t='txt', x=dz, y=hi_r, s='requested cores: %.1f to %.1f' % (lo_r, hi_r), n='%.0f to %.0f cores' % (lo_r, hi_r),
                  al='right', bl='bottom', dy=-6, c='b', ax='R'))
    def at(day):
        return next(n for d, n, _ in pts if d >= day)
    aria = ('Specimen drift over %d days at a 50 percent target with the vertical autoscaler on the same CPU metric, steady demand. '
            'Replicas, log scale, rise in steps: %s, and stop at %s. Requested cores, linear: between %.1f and %.1f throughout.'
            % (dz, ', '.join('day %d %s' % (day, format(int(at(day)), ',')) for day in (0, 5, 10, 15, 20, 25, 30)),
               format(int(nz), ','), lo_r, hi_r))
    cap = ('The specimen\'s drift: 100 cores of steady demand, a 50%% horizontal target and the vertical autoscaler on the same CPU '
           'metric, documented defaults. Replicas, on the left and in logarithms, climb a staircase from %d to %s: one step about '
           'every three and a third days, when the vertical loop\'s percentile lets go of the previous level. Requested cores, '
           'on the right, stay between %.1f and %.1f. The line every capacity dashboard draws is the flat one.'
           % (n0, format(int(nz), ','), lo_r, hi_r))
    FIGS.append(Figure('drift', s, aria, cap))


def fig_coupling():
    """T120: the split pairing's relative gain against the heap's share of observed memory, at the largest theta that share
    allows, for the five OpenJDK 17 collectors measured by Cai and coauthors (2022): a red line for the only one that can break
    the pairing and a gray band for the other four. The 2005 benchmarks stay in the text as history, off the chart."""
    table = {cells(r)[0]: (number(cells(r)[1]), cells(r)[2]) for r in section('T120') if not r.startswith('curve')}
    curve = {}
    for r in section('T120'):
        c = cells(r)
        if c[0] == 'curve':
            curve.setdefault(c[1], []).append((_n(c[2]), _n(c[3])))
    ymax = 10
    edge = number(table['Parallel'][1])
    others = ['Serial', 'G1', 'Shenandoah', 'ZGC']
    shares = [x for x, _ in curve['G1']]
    low = [min(dict(curve[n])[x] for n in others) for x in shares]
    high = [max(dict(curve[n])[x] for n in others) for x in shares]
    s = base('chart-coupling', 320, ml=(40, 48), mr=(14, 16))
    s['X'] = dict(lo=0, hi=1.0, ticks=[[v, _pct(v)] for v in (0, 0.25, 0.5, 0.75, 1.0)],
                  title="heap's share of the memory a pod uses", ntitle='heap share')
    s['Y'] = dict(lo=0, hi=ymax, ticks=[[v, '%d' % v] for v in (0, 1, 2, 4, 6, 8, 10)],
                  title='relative gain of the CPU loop (1: the loops are independent)', ntitle='relative gain')
    e = s['els']
    e.append(dict(t='rect', x0=0, x1=edge, y0=0, y1=ymax, c='a', al=0.08))
    e.append(dict(t='vline', x=edge, c='a'))
    e.append(dict(t='txt', x=0.01, y=ymax - 0.3, s='reversed for Parallel', n='reversed', al='left', bl='top', c='a', b=True))
    e.append(dict(t='txt', x=edge, y=0.25, s='singular at a %.1f%% heap' % (100 * edge), n='%.1f%%' % (100 * edge),
                  al='left', bl='bottom', dx=5, c='a', b=True))
    e.append(dict(t='hline', y=1, c='g', w=1, dash=True))
    e.append(dict(t='band', pts=[[x, lo, hi] for x, lo, hi in zip(shares, low, high)], c='g', al=0.35))
    e.append(dict(t='line', pts=[[x, v] for x, v in curve['Parallel'] if x > edge and v <= ymax], c='a', w=3))
    legend = (('red: Parallel collector, OpenJDK 17', 'red: Parallel', 'a', True),
              ('gray band: Serial, G1, Shenandoah, ZGC, OpenJDK 17', 'gray: the others', 'sub', False))
    for row, (text, short, col, bold) in enumerate(legend):
        e.append(dict(t='txt', x=0.45, y=round(ymax - 0.6 - 0.8 * row, 1), s=text, n=short, al='left', bl='middle', c=col, b=bold))
    aria = ("Relative gain of the CPU loop in the split pairing against the heap's share of the memory a pod uses, for a live set "
            'that does not follow load, at the largest coupling that share allows; a gain of 1 means the loops are independent. '
            'Collectors of OpenJDK 17, measured by Cai and coauthors in 2022. %s. '
            'Only the Parallel collector turns singular, at a heap of %.1f%% of memory, and is reversed below it.'
            % ('; '.join('%s, beta %.2f: %s' % (n, table[n][0], ', '.join('%s at %s' % (_g(round(dict(curve[n])[x], 2)), _pct(x))
                                                                            for x in (0.25, 0.5, 0.75)))
                         for n in ['Parallel'] + others), 100 * edge))
    cap = ('How much the memory autoscaler disturbs the CPU autoscaler, as the heap takes a smaller share of a pod\'s memory. '
           'At 1 the two do not affect each other. For Serial, G1, Shenandoah and ZGC the effect stays small (gray band). Only the '
           'Parallel collector breaks the pairing: with a heap under %.1f%% of memory, the memory autoscaler turns the CPU '
           'autoscaler\'s corrections around. Collector costs: OpenJDK 17, measured by Cai and coauthors.' % (100 * edge))
    FIGS.append(Figure('coupling', s, aria, cap))


def fig_settings():
    """T24: the doubling time against the step interval. At one step factor the bracket is a wedge through
    the origin; the margin changes the factor and with it the slope."""
    rows = []
    for row in section('T24'):
        c = cells(row)
        rows.append((c[0], number(c[1]), number(c[2]), number(c[3]), number(c[4]), number(c[5])))
    base_factor = rows[0][2]
    lo_slope, hi_slope = rows[0][3] / rows[0][1], rows[0][5] / rows[0][1]
    names = {'documented defaults': ('defaults', 'defaults'), 'percentile 0.5': ('50th percentile', 'p50'),
             'percentile 0.95': ('95th percentile', 'p95'), 'half-life 12.0': ('half-life 12 h', '12 h'),
             'half-life 48.0': ('half-life 48 h', '48 h'), 'margin 0.0': ('margin 0, factor 2', 'm 0'),
             'margin 0.3': ('margin 0.3, factor 1.54', 'm 0.3')}
    s = base('chart-settings', 320, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=0, hi=175, ticks=[[v, '%d' % v] for v in (0, 40, 80, 120, 160)],
                  title='hours between steps, h log2(1/(1-p))', ntitle='hours between steps')
    s['Y'] = dict(lo=0, hi=235, ticks=[[v, '%d' % v] for v in (0, 50, 100, 150, 200)],
                  title='hours to double the replicas', ntitle='doubling, hours')
    e = s['els']
    e.append(dict(t='band', pts=[[0, 0, 0], [175, round(175 * lo_slope, 2), round(175 * hi_slope, 2)]], c='b', al=0.12, edge=True))
    for name, step, factor, lo, sim, hi in rows:
        col = 'b' if factor == base_factor else 'd'
        e.append(dict(t='line', pts=[[step, lo], [step, hi]], c=col, w=3))
        e.append(dict(t='pt', x=step, y=sim, r=4, c=col))
        label, short = names[name]
        left = name in ('margin 0.0', 'margin 0.3', 'half-life 48.0')
        e.append(dict(t='txt', x=step, y=sim, s=label, n=short, al='right' if left else 'left', dx=-8 if left else 8, c=col,
                      b=name == 'documented defaults'))
    e.append(dict(t='txt', x=4, y=222, s='band: the bracket at step factor %.3f, from the closed form' % base_factor,
                  n='band: factor %.2f' % base_factor, al='left', c='sub'))
    aria = ('Hours for the replica count to double against hours between steps, target 0.5, steady demand. Band: the closed-form bracket '
            'at step factor %.3f. Bars: each setting\'s bracket, dots: simulated. %s.'
            % (base_factor, '; '.join('%s: step %.1f h, bracket %.1f to %.1f, simulated %.1f' % (n, st, lo, hi, sm)
                                      for n, st, f, lo, sm, hi in rows)))
    cap = ('The staircase away from the defaults: each setting\'s doubling time against the hours between its steps. A different '
           'percentile or half-life moves along the band, in proportion. The margin changes the slope instead: zero doubles the '
           'replicas at every step, 0.3 multiplies them by 1.54. Bars are the closed form, dots the simulation, which rounds the replica '
           'count up and can dip just under its bar.')
    FIGS.append(Figure('settings', s, aria, cap))


def fig_tail_regimes():
    """T90 and T92: q against the lognormal shape, with the band in which a 50% target rests. The curve rises
    through the band and falls back through it, which is the reentrant diagram of Proposition 5."""
    pts = {}
    for row in section('T92'):
        c = cells(row)
        if c[0] == 'frontier':
            pts[number(c[1])] = number(c[2])
    edges = []
    for row in section('T90'):
        c = cells(row)
        if c[0] == 'regime' and c[1] == '0.5':
            pts[number(c[2])] = number(c[3])
        if c[0] == 'edges' and c[1] == '0.5':
            edges = [float(x) for x in c[2].split(', ')]
    curve = sorted(pts.items())
    m, tol, u = 0.15, 0.1, 0.5   # the margin and tolerance T90 states, at a 50% target
    lo, hi = 1 / ((1 + m) * u * (1 + tol)), 1 / ((1 + m) * u * (1 - tol))
    s = base('chart-tail-regimes', 320, ml=(40, 48), mr=(14, 16))
    e = s['els']
    e.append(dict(t='hband', y0=round(lo, 4), y1=round(hi, 4), c='c', al=0.18))
    for x in edges:
        e.append(dict(t='vline', x=x, c='g'))
    z = 1.2816   # the standard normal quantile of the 90th percentile, as T90 states it
    smooth = [[round(i * 0.05, 2), round(math.exp(z * i * 0.05 - (i * 0.05) ** 2 / 2), 4)] for i in range(53)]
    e.append(dict(t='line', pts=smooth, c='b'))
    for x, y in curve:
        e.append(dict(t='pt', x=x, y=y, r=3.5, c='b'))
    names = (('drift up', 'up'), ('rest', 'rest'), ('drift down', 'down'), ('rest', 'rest'), ('drift up', 'up'))
    bounds = [0.0] + edges + [2.6]
    for (name, short), a, b in zip(names, bounds[:-1], bounds[1:]):
        e.append(dict(t='txt', x=round((a + b) / 2, 4), y=2.45, s=name, n=short, al='center', bl='middle', c='ink'))
    e.append(dict(t='txt', x=1.05, y=round((lo + hi) / 2, 4), s='a 50% target rests', n='rests', al='center', bl='middle', c='c'))
    s['X'] = dict(lo=0, hi=2.6, ticks=[[v, _g(v)] for v in (0, 0.5, 1, 1.5, 2, 2.5)],
                  title='lognormal shape of per-pod usage: how heavy its tail is', ntitle='tail shape')
    s['Y'] = dict(lo=0.9, hi=2.55, ticks=[[v, _g(v)] for v in (1, 1.5, 2, 2.5)],
                  title='q: 90th percentile of usage over its mean', ntitle='q')
    _id_last(s)
    aria = ('The 90th percentile of per-pod usage over its mean against the lognormal shape of per-pod usage. %s. A 50%% target rests '
            'while q lies between %.3f and %.3f, which the curve crosses at shapes %s.'
            % ('; '.join('%s: %.3f' % (_g(x), y) for x, y in curve), lo, hi, ', '.join('%.2f' % x for x in edges)))
    cap = ('How the tail of per-pod usage decides what the pair does. The curve is the 90th percentile over the mean; the shaded band '
           'is where a 50%% target rests, and the dots are the values the model computes. Below the band the pair drifts up, above it the pair drifts down. As the tail grows the curve '
           'rises through the band, peaks at %.2f, and falls back through it, so one setting drifts up, rests, drifts down, rests and '
           'drifts up again. The branches past a shape of 1.2 need pods with no CPU limit on nodes large enough not to clip the '
           'samples.' % max(y for _, y in curve))
    FIGS.append(Figure('tail-regimes', s, aria, cap))


# ---------- Part 2 ----------

def fig_nested():
    rows = [cells(r) for r in section('T6')]
    k = [number(r[0]) for r in rows]
    ample = [number(r[2]) for r in rows]
    nest = [number(r[3]) for r in rows]
    sep = [number(r[5]) for r in rows]
    rounds = [int(r[1]) for r in rows]
    s = base('chart-nested', 320, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=2.6, hi=120, log=True, ticks=[[v, '%dx' % v] for v in k], title='surge, log scale', ntitle='surge (log)')
    s['Y'] = dict(lo=0, hi=2000, ticks=[[v, '%d s' % v] for v in (0, 500, 1000, 1500, 2000)], title='time until capacity meets the surge', ntitle='time to capacity')
    e = s['els']
    for ys, c, lab, nlab in ((nest, 'a', 'nested: every round waits for nodes', 'nested'),
                             (sep, 'b', 'node loop sees the final need', 'final need'),
                             (ample, 'g', 'ample nodes', 'ample')):
        e.append(dict(t='line', pts=[[a, b] for a, b in zip(k, ys)], c=c, mk=3))
        e.append(dict(t='txt', x=k[-1], y=ys[-1], s=lab, n=nlab, al='right', bl='bottom', dx=-2, dy=-8, c=c, b=c == 'a'))
    for a, b, r in zip(k, nest, rounds):
        if a < k[-1]:
            e.append(dict(t='txt', x=a, y=b, s='%d round%s' % (r, '' if r == 1 else 's'), n='%d' % r, al='right', bl='bottom', dx=-4, dy=-4, c='a'))
    aria = ('Time until capacity meets a surge, against its size, for a pod loop nested in a node loop with no free slots. Nested: %s. '
            'Node loop that sees the final need: %s. Ample nodes: %s.' % (
                ', '.join('%dx %d s' % (a, b) for a, b in zip(k, nest)), ', '.join('%dx %d s' % (a, b) for a, b in zip(k, sep)),
                ', '.join('%dx %d s' % (a, b) for a, b in zip(k, ample))))
    cap = ('Time until capacity meets a surge, against the surge\'s size, with 90-second pods and 210-second nodes and no free slots. '
           'With ample nodes each round costs a pod\'s dead time. A node loop that saw the final need would add one node wait. '
           'The node loop as documented sees only the pods already pending, so every round waits for nodes, and the gap grows with every round.')
    FIGS.append(Figure('nested', s, aria, cap))


def fig_node_time():
    rows = [cells(r) for r in section('T7')]
    tn = [number(r[0]) for r in rows]
    nest = [number(r[1]) for r in rows]
    sep = [number(r[3]) for r in rows]
    ample = number(rows[0][4])
    s = base('chart-node-time', 320, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=0, hi=640, ticks=[[v, '%d s' % v] for v in (0, 120, 240, 360, 480, 600)], title='node provisioning time', ntitle='node time')
    s['Y'] = dict(lo=0, hi=3000, ticks=[[v, '%d s' % v] for v in (0, 1000, 2000, 3000)], title='time until capacity meets a 30x surge', ntitle='time to capacity')
    e = s['els']
    e.append(dict(t='hline', y=ample, c='g', w=1, dash=True))
    e.append(dict(t='txt', x=640, y=ample, s='ample nodes: %d s' % ample, n='ample', al='right', bl='bottom', dy=-4, c='g'))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(tn, nest)], c='a', mk=3))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(tn, sep)], c='b', mk=3))
    e.append(dict(t='txt', x=tn[-1], y=nest[-1], s='nested: %d s' % nest[-1], n='nested', al='right', bl='bottom', dx=-6, dy=-6, c='a', b=True))
    e.append(dict(t='txt', x=tn[-1], y=sep[-1], s='final need: %d s' % sep[-1], n='final need', al='right', bl='bottom', dx=-6, dy=-6, c='b'))
    i = tn.index(210.0) if 210.0 in tn else 3
    e.append(dict(t='txt', x=tn[i], y=nest[i], s='%d s at 210 s' % nest[i], n='', al='right', bl='bottom', dx=-6, dy=-4, c='a'))
    aria = ('Time until capacity meets a 30x surge against node provisioning time. Nested: %s. Node loop that sees the final need: %s. Ample nodes: %d s.' % (
        ', '.join('%d s: %d s' % (a, b) for a, b in zip(tn, nest)), ', '.join('%d s: %d s' % (a, b) for a, b in zip(tn, sep)), ample))
    cap = ('Time until capacity meets a 30x surge, four rounds, as node provisioning gets slower. The documented pairing pays the node time '
           'once per round, so its line climbs four times as steeply as a node loop that saw the final need, which pays it once. '
           'The pod loop\'s effective dead time is its own plus the node loop\'s.')
    FIGS.append(Figure('node-time', s, aria, cap))


def fig_headroom():
    """T8 simulated against T121's closed-form steps: each covered round saves a node wait once the slots reach its step,
    and a slot count just short of a step is slower than the step below it."""
    n0 = 64
    pts = []
    for r in section('T8'):
        c = cells(r)
        if c[0] == '30':
            pts.append((int(c[1]), int(c[4])))
    steps = [(int(cells(r)[3]), int(cells(r)[4]), int(cells(r)[5])) for r in section('T121') if cells(r)[0] == '30']
    none = dict(pts)[0]
    stair = [[0, none]]
    level = none
    for slots, after, _ in steps:
        stair += [[round(slots / n0, 4), level], [round(slots / n0, 4), after]]
        level = after
    stair.append([14.6, level])
    levels = [none] + [after for _, after, _ in steps]
    s = base('chart-headroom', 320, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=-0.3, hi=14.6, ticks=[[v, '%d x' % v] for v in (0, 2, 4, 6, 8, 10, 12, 14)], title='free slots held in advance, as a multiple of the running pods', ntitle='free slots (x pods)')
    s['Y'] = dict(lo=300, hi=1400, ticks=[[v, '%d s' % v] for v in (400, 600, 800, 1000, 1200)], title='time until capacity meets a 30x surge', ntitle='time to capacity')
    e = s['els']
    e.append(dict(t='line', pts=stair, c='b', w=1.5, dash=True))
    short = []
    for slots, t in pts:
        prev = [lv for st, lv in zip([0] + [x for x, _, _ in steps], levels) if st <= slots]
        expected = prev[-1]
        if t > expected:
            short.append((slots, t))
            e.append(dict(t='pt', x=round(slots / n0, 4), y=t, r=5, c='a'))
        else:
            e.append(dict(t='pt', x=round(slots / n0, 4), y=t, r=4, c='b'))
    first = short[0]
    e.append(dict(t='txt', x=round(first[0] / n0, 4), y=first[1], s='%d slots, just short of a step: %d s, slower than none' % first,
                  n='%d slots: %d s' % first, al='left', bl='bottom', dx=8, dy=-2, c='a', b=True))
    e.append(dict(t='txt', x=round(steps[0][0] / n0, 4), y=steps[0][1], s='each step saves a node wait: %s slots'
                  % ', '.join('%d' % st for st, _, _ in steps), n='steps', al='left', bl='top', dx=8, dy=6, c='b'))
    last = pts[-1]
    e.append(dict(t='txt', x=round(last[0] / n0, 4), y=last[1], s='%d slots, %d x: %d s' % (last[0], round(last[0] / n0), last[1]),
                  n='%d x: %d s' % (round(last[0] / n0), last[1]), al='right', bl='bottom', dx=-8, dy=-8, c='b'))
    aria = ('Time until capacity meets a 30x surge against free slots held in advance, as a multiple of 64 running pods. Closed-form steps at '
            '%s slots, to %s seconds. Simulated: %s. Just short of a step, %s.'
            % (', '.join('%d' % st for st, _, _ in steps), ', '.join('%d' % lv for lv in levels),
               '; '.join('%d slots: %d s' % p for p in pts), '; '.join('%d slots take %d s' % p for p in short)))
    cap = ('Time until capacity meets a 30x surge against free slots held in advance. Each step of the dashed staircase saves one node '
           'wait and costs more slots than the last: removing every wait takes 14 times the running pods. The simulation (dots) sits on '
           'the steps, and just short of a step it is slower than the step below (red).')
    FIGS.append(Figure('headroom', s, aria, cap))


def fig_second_surge():
    rows = [cells(r) for r in section('T28') if number(cells(r)[0]) <= 1200]
    gap = [number(r[0]) for r in rows]
    closed = [number(r[2]) for r in rows]
    inst = [number(r[3]) for r in rows]
    bulk = [number(r[4]) for r in rows]
    held = [number(r[5]) for r in rows]
    s = base('chart-second-surge', 340, ml=(44, 52), mr=(40, 56))
    s['X'] = dict(lo=0, hi=1250, ticks=[[v, '%d s' % v] for v in (0, 300, 600, 900, 1200)], title='gap between the two surges', ntitle='gap')
    s['Y'] = dict(lo=0, hi=1400, ticks=[[v, '%d s' % v] for v in (0, 360, 570, 780, 990, 1200)], title='time until capacity meets the second surge', ntitle='time to capacity', col='a')
    s['R'] = dict(lo=0, hi=17.5, ticks=[[v, '%d h' % v] for v in (0, 5, 10, 15)], title='node-hours held in the gap', ntitle='node-hours', col='g')
    e = s['els']
    e.append(dict(t='vline', x=300, c='g', dash=True))
    e.append(dict(t='vline', x=900, c='g', dash=True))
    e.append(dict(t='txt', x=300, y=1400, s='pods removed', n='pods go', al='left', bl='top', dx=4, dy=4, c='g'))
    e.append(dict(t='txt', x=300, y=1400, s='pods still up: 0 s', n='pods up: 0 s', al='right', bl='top', dx=-4, dy=4, c='a'))
    e.append(dict(t='txt', x=900, y=1400, s='nodes deleted', n='nodes go', al='left', bl='top', dx=4, dy=4, c='g'))
    step = []
    for i, (x, y) in enumerate(zip(gap, closed)):
        if i:
            step.append([x, closed[i - 1]])
        step.append([x, y])
    step.append([1250, closed[-1]])
    e.append(dict(t='line', pts=step, c='a', w=2))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(gap, held)] + [[1250, held[-1]]], c='g', w=1.5, dash=True, ax='R'))
    for x, a, b in zip(gap, inst, bulk):
        e.append(dict(t='pt', x=x, y=a, r=3.5, c='a'))
        if b != a:
            e.append(dict(t='pt', x=x, y=b, r=4.5, c='b', open=True))
    e.append(dict(t='txt', x=480, y=360, s='nodes still there: %d s' % closed[gap.index(450)], n='%d s' % closed[gap.index(450)], al='center', bl='top', dy=8, c='a', b=True))
    e.append(dict(t='txt', x=1200, y=1200, s='fully nested: %d s' % closed[-1], n='nested', al='right', bl='bottom', dx=-4, dy=-8, c='a', b=True))
    e.append(dict(t='txt', x=1240, y=held[-1], s='held: %.1f node-hours' % held[-1], n='', al='right', bl='top', dy=6, c='g', ax='R'))
    aria = ('Time until capacity meets a second 30x surge, against the gap after the first, with the default 300-second pod stabilization and '
            '600-second node unneeded time. Closed form: %s. Simulated with instant deletion: %s. With the documented bulk of 10 nodes per scan: %s. '
            'Node-hours held in the gap: %s.' % (
                ', '.join('%d s: %d s' % (a, b) for a, b in zip(gap, closed)), ', '.join('%d s: %d s' % (a, b) for a, b in zip(gap, inst)),
                ', '.join('%d s: %d s' % (a, b) for a, b in zip(gap, bulk)), ', '.join('%d s: %.1f' % (a, b) for a, b in zip(gap, held))))
    cap = ('Time until capacity meets a second 30x surge (red, left axis) and the node-hours held in the gap (gray dashed, right axis). '
           'While the first surge\'s pods are still up, the second costs nothing. After that, each round the leftover nodes no longer '
           'cover adds a 210-second node wait, while the node-hours keep rising. Open blue points: the documented bulk deletion, which '
           'only shifts the steps.')
    FIGS.append(Figure('second-surge', s, aria, cap))


def fig_unneeded():
    rows = [cells(r) for r in section('T29')]
    pts = [(int(number(r[0])), number(r[2]), number(r[3]), r[4].strip()) for r in rows]
    s = base('chart-unneeded', 320, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=3, hi=21, ticks=[[v, '%d h' % v] for v in (5, 10, 15, 20)], title='node-hours held in a 1200-second gap', ntitle='node-hours')
    s['Y'] = dict(lo=200, hi=1400, ticks=[[v, '%d s' % v] for v in (360, 570, 780, 1200)], title='time until capacity meets the second surge', ntitle='time to capacity')
    e = s['els']
    eff = [p for p in pts if p[3] == 'none']
    lo, hi = min(eff, key=lambda p: p[2]), max(eff, key=lambda p: p[2])
    for u, t, h, by in pts:
        e.append(dict(t='pt', x=h, y=t, r=4.5 if by == 'none' else 3.5, c='b' if by == 'none' else 'a', open=by != 'none'))
    e.append(dict(t='txt', x=lo[2], y=lo[1], s='release at once: %.2f h, %d s' % (lo[2], lo[1]), n='release', al='left', bl='top', dx=6, dy=8, c='b', b=True))
    e.append(dict(t='txt', x=hi[2], y=hi[1], s='hold through the gap: %.2f h, %d s' % (hi[2], hi[1]), n='hold', al='right', bl='top', dx=-8, dy=8, c='b', b=True))
    e.append(dict(t='txt', x=12, y=1200, s='unneeded 60 to 900 s: more hours, no gain', n='dominated', al='center', bl='bottom', dy=-10, c='a'))
    e.append(dict(t='txt', x=hi[2], y=675, s='1000 to 1170 s: same hours, slower', n='dominated', al='right', bl='middle', dx=-10, c='a'))
    aria = ('Node-hours held against time until capacity meets a second 30x surge 1200 seconds after the first, one point per unneeded time. %s. '
            'Only releasing at once and holding through the gap are efficient.' % '; '.join('%d s: %.2f node-hours, %d s' % (u, h, t) for u, t, h, _ in pts))
    cap = ('Each point is one setting of the node loop\'s unneeded time, for a second surge 1200 seconds after the first. Holding nodes '
           'past the pod loop\'s window costs node-hours; it pays only once it covers the whole ramp. Every setting in between costs more '
           'than releasing at once without being faster, or as much as holding through the gap while slower. The two solid points are the frontier.')
    FIGS.append(Figure('unneeded', s, aria, cap))


def fig_memoryless():
    rows = [cells(r) for r in section('T30')]
    s = base('chart-memoryless', 330, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=0, hi=32, ticks=[[v, '%d h' % v] for v in (0, 5, 10, 15, 20, 25, 30)], title='expected node-hours held between surges', ntitle='node-hours')
    s['Y'] = dict(lo=0, hi=1200, ticks=[[v, '%d s' % v] for v in (0, 300, 600, 900, 1200)], title='expected time until capacity meets the second surge', ntitle='expected time')
    e = s['els']
    desc = []
    for mu, c in (('600', 'b'), ('1800', 'a')):
        pts = [(r[1], number(r[2]), number(r[4])) for r in rows if r[0] == mu]
        first, last = pts[0], pts[-1]
        e.append(dict(t='line', pts=[[first[1], first[2]], [last[1], last[2]]], c='g', w=1, dash=True))
        e.append(dict(t='line', pts=[[h, t] for _, h, t in pts], c=c, w=2, mk=3))
        d = [p for p in pts if p[0] == '600'][0]
        e.append(dict(t='pt', x=d[1], y=d[2], r=6.5, c=c, open=True))
        e.append(dict(t='txt', x=d[1], y=d[2], s='600 s default', n='600 s', al='left', bl='bottom', dx=8, dy=-4, c=c))
        e.append(dict(t='txt', x=last[1], y=last[2], s='mean gap %s s: hold forever' % mu, n='%s s gap' % mu, al='left' if mu == '600' else 'right', bl='top', dx=6 if mu == '600' else -2, dy=10, c=c, b=True))
        desc.append('mean gap %s s: %s' % (mu, '; '.join('unneeded %s s %.2f node-hours %.1f s' % p for p in pts)))
    e.append(dict(t='txt', x=4.4, y=1015.8, s='release at once', n='release', al='left', bl='bottom', dx=8, dy=-8, c='a'))
    aria = ('Expected node-hours held against expected time to capacity for a second 30x surge, gaps exponential, one point per unneeded time. %s. '
            'Dashed lines join releasing at once to holding forever; every intermediate point lies above them.' % '. '.join(desc))
    cap = ('Each line traces the unneeded time from 0 to forever for memoryless gaps with a mean of 600 or 1,800 seconds. Every '
           'intermediate setting, the 600-second default marked, lies above the dashed line joining the two ends, so no exchange rate '
           'between node-hours and seconds makes it the cheapest. The cheapest setting is one end or the other.')
    FIGS.append(Figure('memoryless', s, aria, cap))


def fig_worst_gap():
    rows = [cells(r) for r in section('T31')]
    lam = [number(r[0]) for r in rows]
    be = [number(r[2]) for r in rows]
    dflt = [number(r[5]) for r in rows]
    zero = [number(r[6]) for r in rows]
    s = base('chart-worst-gap', 320, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=3.2, hi=320, log=True, ticks=[[v, '%g' % v] for v in lam], title='exchange rate: node-seconds per second short of capacity, log scale', ntitle='exchange rate (log)')
    s['Y'] = dict(lo=1, hi=3.2, ticks=[[v, '%.1f' % v] for v in (1.0, 1.5, 2.0, 2.5, 3.0)], title='worst cost over all gaps, as a multiple of knowing the gap', ntitle='worst ratio')
    e = s['els']
    e.append(dict(t='hline', y=2, c='g', w=1, dash=True))
    e.append(dict(t='txt', x=4, y=2, s='twice the hindsight cost', n='2x', al='left', bl='top', dy=4, c='g'))
    for ys, c, lab, nlab, dy in ((zero, 'g', 'release at once', 'release', -8), (dflt, 'a', '600 s default', 'default', -8), (be, 'b', 'break-even holding', 'break-even', 10)):
        e.append(dict(t='line', pts=[[a, b] for a, b in zip(lam, ys)], c=c, mk=3))
        e.append(dict(t='txt', x=lam[-1], y=ys[-1], s=lab, n=nlab, al='right', bl='top' if dy > 0 else 'bottom', dx=-8, dy=dy, c=c, b=c == 'b'))
    aria = ('Worst cost over all gaps as a multiple of the cost with the gap known, against the exchange rate. Break-even holding: %s. '
            'The 600-second default: %s. Releasing at once: %s.' % tuple(', '.join('%g: %.3f' % (a, b) for a, b in zip(lam, ys)) for ys in (be, dflt, zero)))
    cap = ('The worst a setting can do, over every gap, against the cost of knowing the gap. Holding for the break-even time stays under '
           'twice the hindsight cost at every exchange rate. The 600-second default matches it only at the one rate, about 41 node-seconds '
           'per second, for which it is the break-even. Releasing at once exceeds twice the hindsight cost at high rates.')
    FIGS.append(Figure('worst-gap', s, aria, cap))


def fig_pod_memory():
    nodes = [(r[1], number(r[2]), number(r[4])) for r in (cells(x) for x in section('T30')) if r[0] == '1800']
    pods = [(r[1], r[2], number(r[3]), number(r[4])) for r in (cells(x) for x in section('T34')) if r[0] == '1800']
    s = base('chart-pod-memory', 330, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=0, hi=32, ticks=[[v, '%d h' % v] for v in (0, 5, 10, 15, 20, 25, 30)], title='expected node-hours held between surges, mean gap 1800 s', ntitle='node-hours')
    s['Y'] = dict(lo=0, hi=1300, ticks=[[v, '%d s' % v] for v in (0, 300, 600, 900, 1200)], title='expected time until capacity meets the second surge', ntitle='expected time')
    e = s['els']
    e.append(dict(t='line', pts=[[h, t] for _, h, t in nodes], c='a', w=2, mk=3))
    e.append(dict(t='line', pts=[[h, t] for _, _, h, t in pods], c='b', w=2, mk=3))
    d = [p for p in nodes if p[0] == '600'][0]
    q = [p for p in pods if p[0] == '900' and p[1] == '0'][0]
    cap = [p for p in pods if p[0] == '3600' and p[1] == '0'][0]
    e.append(dict(t='pt', x=d[1], y=d[2], r=6.5, c='a', open=True))
    e.append(dict(t='pt', x=q[2], y=q[3], r=6.5, c='b', open=True))
    e.append(dict(t='txt', x=d[1], y=d[2], s='default, 300 s pods + 600 s nodes: %d s' % round(d[2]), n='default: %d s' % round(d[2]), al='left', bl='bottom', dx=8, dy=-6, c='a', b=True))
    e.append(dict(t='txt', x=q[2], y=q[3], s='900 s of pods, same hours: %d s' % round(q[3]), n='pods: %d s' % round(q[3]), al='right', bl='top', dx=-8, dy=6, c='b', b=True))
    e.append(dict(t='txt', x=cap[2], y=cap[3], s='window cap, 3600 s', n='cap', al='right', bl='top', dx=-6, dy=8, c='b'))
    e.append(dict(t='txt', x=0, y=1200, s='release at once', n='', al='left', bl='bottom', dx=6, dy=-6, c='b'))
    aria = ('Expected node-hours held against expected time to capacity for a second 30x surge, gaps exponential with a mean of 1800 s. '
            'Memory kept as nodes after the default 300-second pod window: %s. Memory kept as pods first, up to the 3600-second cap, then as nodes: %s.' % (
                '; '.join('unneeded %s s %.2f node-hours %.1f s' % p for p in nodes),
                '; '.join('stabilization %s s unneeded %s s %.2f node-hours %.1f s' % p for p in pods)))
    cap_txt = ('Two ways to keep the same memory after a surge, for gaps with a mean of 1,800 seconds. Red keeps it as empty nodes behind the '
               'default five-minute pod window; blue keeps it as pods first, up to the one-hour cap on the window, and as nodes after that. At every '
               'amount of node-hours blue is faster: the default\'s 11.41 node-hours buy 855 seconds as nodes and 728 as pods.')
    FIGS.append(Figure('pod-memory', s, aria, cap_txt))


def fig_hazard():
    rows = [cells(r) for r in section('T37')]
    s = base('chart-hazard', 340, ml=(44, 52), mr=(14, 16))
    s['X'] = dict(lo=0, hi=3700, ticks=[[v, '%d s' % v] for v in (0, 600, 1200, 1800, 2400, 3000, 3600)], title='pod scale-down window (the memory, kept as pods)', ntitle='window')
    s['Y'] = dict(lo=0.6, hi=1.8, ticks=[[v, '%.1f' % v] for v in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8)], title='expected cost as a multiple of releasing at once', ntitle='cost / release')
    e = s['els']
    e.append(dict(t='hline', y=1.0, c='g', w=1, dash=True))
    style = {'0.5': ('b', 'shape 0.5: surges cluster', 'max'), '0.7': ('c', 'shape 0.7', 'end'), '1.0': ('g', 'shape 1: memoryless', 'mid'),
             '1.5': ('d', 'shape 1.5', 'peak'), '3.0': ('a', 'shape 3: near-periodic', 'peak')}
    desc = []
    for shape, (c, lab, where) in style.items():
        pts = [(number(r[1]), number(r[2])) for r in rows if r[0] == shape]
        e.append(dict(t='line', pts=[[x, y] for x, y in pts], c=c, w=2, mk=2.5))
        lo = min(pts, key=lambda p: p[1])
        hi = max(pts, key=lambda p: p[1])
        if where == 'max':
            e.append(dict(t='pt', x=lo[0], y=lo[1], r=6, c=c, open=True))
            e.append(dict(t='txt', x=lo[0], y=lo[1], s='%s, least at %d s: %.3f' % (lab, lo[0], lo[1]), n='0.5: %d s' % lo[0], al='left', bl='top', dx=8, dy=6, c=c, b=True))
        elif where == 'end':
            e.append(dict(t='txt', x=pts[-1][0], y=pts[-1][1], s=lab, n='0.7', al='right', bl='bottom', dx=-4, dy=-6, c=c))
        elif where == 'mid':
            m = [p for p in pts if p[0] == 1800][0]
            e.append(dict(t='txt', x=m[0], y=m[1], s=lab, n='1', al='left', bl='top', dx=4, dy=8, c=c))
        else:
            e.append(dict(t='txt', x=hi[0], y=hi[1], s=lab, n='shape 3.0' if shape == '3.0' else shape, al='center', bl='bottom', dy=-8, c=c, b=shape == '3.0'))
        desc.append('shape %s: %s' % (shape, ', '.join('%d s %.3f' % p for p in pts)))
    aria = ('Expected cost of keeping the post-surge memory as pods, as a multiple of releasing at once, against the window, for Weibull gaps with a mean of 1800 s '
            'and an exchange rate of 64. %s.' % '; '.join(desc))
    cap = ('Expected cost against the pod scale-down window for gaps of five shapes with the same mean. Where surges cluster (shape below 1) the hazard '
           'falls and the cost has an interior minimum: 487 seconds at shape 0.5, 29% below releasing at once. Where the hazard is constant or rises, '
           'the cost rises first, and the cheapest window is zero or the hour the API allows.')
    FIGS.append(Figure('hazard', s, aria, cap))



def fig_surge_tail():
    tail = [cells(r) for r in section('T94') if cells(r)[0] == 'tail']
    finite = [c for c in tail if c[6] != 'inf']
    s = base('chart-surge-tail', 340, ml=(44, 56), mr=(40, 48))
    e = s['els']
    e.append(dict(t='vline', x=1.0, c='g'))
    e.append(dict(t='txt', x=1.0, y=1500000, s='no finite mean shortfall at or below 1', n='infinite below 1', al='left', bl='middle', dx=6, c='g'))
    for col, c in ((8, 'a'), (7, 'b'), (6, 'g')):
        e.append(dict(t='line', pts=[[_n(r[1]), _n(r[col])] for r in finite], c=c, mk=3))
    last = finite[-1]
    mid = [r for r in finite if _n(r[1]) == 2.0][0]
    e.append(dict(t='txt', x=_n(last[1]), y=_n(last[8]), s='nested', n='nested', al='right', bl='bottom', dx=-4, dy=-6, c='a', b=True))
    e.append(dict(t='txt', x=_n(mid[1]), y=_n(mid[7]), s='final need', n='final need', al='left', bl='top', dx=4, dy=4, c='b'))
    e.append(dict(t='txt', x=_n(last[1]), y=_n(last[6]), s='ample nodes', n='ample', al='right', bl='top', dx=-4, dy=4, c='g'))
    e.append(dict(t='line', ax='R', pts=[[_n(r[1]), _n(r[5])] for r in tail], c='c', mk=3, dash=True))
    first = tail[0]
    e.append(dict(t='txt', ax='R', x=_n(first[1]), y=_n(first[5]), s='%s s' % first[5], n='%s s' % first[5],
                  al='left', bl='bottom', dx=4, dy=-6, c='c', b=True))
    two = [r for r in tail if _n(r[1]) == 2.0][0]
    e.append(dict(t='txt', ax='R', x=2.0, y=_n(two[5]), s='mean time to capacity, right axis', n='time, right axis',
                  al='left', bl='bottom', dx=4, dy=-6, c='c'))
    s['X'] = dict(lo=0.6, hi=3.1, ticks=[[0.69, '0.69'], [1.0, '1'], [1.5, '1.5'], [2.0, '2'], [2.5, '2.5'], [3.0, '3']],
                  title='tail exponent of surge sizes', ntitle='tail exponent')
    s['Y'] = dict(lo=500, hi=3000000, log=True, ticks=[[1000, '1k'], [10000, '10k'], [100000, '100k'], [1000000, '1M']],
                  title='mean pod-seconds short', ntitle='pod-s short')
    s['R'] = dict(lo=0, hi=1000, col='c', ticks=[[v, '%d s' % v] for v in (0, 250, 500, 750, 1000)], title='mean time to capacity', ntitle='mean time')
    _id_last(s)
    aria = ('Mean pod-seconds short (left, log scale) and mean nested time to capacity (right) against the tail exponent of surge sizes. '
            'Nested: %s. Node loop that sees the final need: %s. Ample nodes: %s. Mean nested time: %s. At or below an exponent of 1 the '
            'mean shortfall is infinite.'
            % (', '.join('%s: %s' % (_g(_n(r[1])), r[8]) for r in finite), ', '.join(r[7] for r in finite),
               ', '.join(r[6] for r in finite), ', '.join('%s: %s s' % (_g(_n(r[1])), r[5]) for r in tail)))
    cap = ('Mean pod-seconds short (left axis, log scale) and mean nested time to capacity (green, right axis) as the tail of surge sizes '
           'gets heavier toward the left. The time stays finite at every exponent, %s seconds at the Borg trace\'s %s. The shortfall grows '
           'without bound as the exponent falls to 1 and has no mean below it, and nesting widens its gap over a node loop that saw the '
           'final need.' % (first[5], _g(_n(first[1]))))
    FIGS.append(Figure('surge-tail', s, aria, cap))


def fig_cover_frontier():
    data = {}
    for r in section('T95'):
        c = cells(r)
        data.setdefault(int(c[0]), []).append((_n(c[1]), _n(c[2]), int(c[3]), int(c[4])))
    s = base('chart-cover-frontier', 320, ml=(44, 52), mr=(14, 16))
    e = s['els']
    for price, col in ((1000, 'b'), (100, 'a'), (10, 'g')):
        e.append(dict(t='line', pts=[[a, x] for a, x, _, _ in data[price]], c=col, mk=3))
    for price, col, bold in ((1000, 'b', False), (100, 'a', True), (10, 'g', False)):
        a, x, _, _ = data[price][-1]
        el = dict(t='txt', x=a, y=x, s='price %d' % price, n='%d' % price, al='right', bl='bottom', dx=-4, dy=-6, c=col)
        if bold:
            el['b'] = True
        e.append(el)
    a, x, rounds, slots = data[100][0]
    e.append(dict(t='txt', x=a, y=x, s='%s rounds, %d slots' % (WORDS[rounds], slots), n='', al='left', bl='middle', dx=8, c='a'))
    s['X'] = dict(lo=1.0, hi=3.1, ticks=[[1.1, '1.1'], [1.5, '1.5'], [2.0, '2'], [2.5, '2.5'], [3.0, '3']],
                  title='tail exponent of surge sizes', ntitle='tail exponent')
    s['Y'] = dict(lo=0.8, hi=700, log=True, ticks=[[1, '1x'], [10, '10x'], [100, '100x']],
                  title='best headroom, 1 + slots / running pods', ntitle='1 + slots / pods')
    _id_last(s)
    aria = ('Optimal headroom against the tail exponent, as x* = 1 + slots over running pods, log scale, for a mean gap of an hour. '
            'Price 10: %s. Price 100: %s. Price 1000: %s.'
            % (', '.join('%s: %.2f' % (_g(a), x) for a, x, _, _ in data[10]), ', '.join('%.2f' % x for _, x, _, _ in data[100]),
               ', '.join('%.2f' % x for _, x, _, _ in data[1000])))
    best = {a: c for a, _, c, _ in data[100]}
    cap = ('The continuous optimum of the headroom, one plus the free slots over the running pods, against the tail exponent, for prices '
           'of 10, 100 and 1,000 slot-seconds per pod-second short and an hour between surges. Each line rises toward a pole at an '
           'exponent of 1, where a further round of headroom buys nothing. At a price of 100 the best whole number of rounds is %s at '
           '1.1, %s at 1.5 and %s at 3.' % (WORDS[best[1.1]], WORDS[best[1.5]], WORDS[best[3.0]]))
    FIGS.append(Figure('cover-frontier', s, aria, cap))


def fig_tail_controller():
    pol = {}
    for r in section('T96'):
        c = cells(r)
        if c[0] == 'policy':
            pol.setdefault(c[2], []).append((_n(c[1]), _n(c[3])))
    s = base('chart-tail-controller', 300, ml=(40, 48), mr=(14, 16))
    e = s['els']
    e.append(dict(t='hline', y=1.0, c='g', dash=True))
    for rule, col in (('peak', 'a'), ('fixed', 'b'), ('mle', 'c')):
        e.append(dict(t='line', pts=[[a, v] for a, v in pol[rule]], c=col, mk=3))
    a, v = pol['peak'][-1]
    e.append(dict(t='txt', x=a, y=v, s='largest surge seen', n='peak', al='right', bl='bottom', dx=-4, dy=-6, c='a', b=True))
    a, v = pol['fixed'][-1]
    e.append(dict(t='txt', x=a, y=v, s='no headroom', n='none', al='right', bl='bottom', dx=-4, dy=-6, c='b'))
    a, v = pol['mle'][-1]
    e.append(dict(t='txt', x=a, y=v, s='estimating controller', n='estimate', al='right', bl='top', dx=-4, dy=6, c='c'))
    s['X'] = dict(lo=1.1, hi=3.1, ticks=[[1.2, '1.2'], [1.5, '1.5'], [2.0, '2'], [2.5, '2.5'], [3.0, '3']],
                  title='tail exponent of surge sizes', ntitle='tail exponent')
    s['Y'] = dict(lo=0.8, hi=4.6, ticks=[[v, '%dx' % v] for v in (1, 2, 3, 4)],
                  title='expected cost over the cost of knowing the exponent', ntitle='cost / oracle')
    _id_last(s)
    aria = ('Expected cost per surge over the cost of knowing the exponent, median of twenty seeds, a thousand surges, against the tail '
            'exponent. Estimating controller: %s. No headroom: %s. Largest surge seen so far: %s.'
            % (', '.join('%s: %.3f' % (_g(a), v) for a, v in pol['mle']), ', '.join('%.3f' % v for _, v in pol['fixed']),
               ', '.join('%.3f' % v for _, v in pol['peak'])))
    worst = max(v for _, v in pol['mle'])
    cap = ('Expected cost per surge of three ways to set the headroom, over the cost of knowing the tail exponent, as the median of '
           'twenty runs of a thousand surges. The controller that re-estimates the exponent after every surge stays within %.1f%%. '
           'Holding none costs about half again as much. Sizing from the largest surge seen so far costs the most, because the largest '
           'of a growing record from a Pareto tail keeps growing.' % (100 * (worst - 1)))
    FIGS.append(Figure('tail-controller', s, aria, cap))


# ---------- Part 3 ----------

def fig_storm():
    rows = [cells(r) for r in section('T41')]
    cost = [number(r[0]) for r in rows]
    ideal = [number(r[4]) for r in rows]
    limited = [number(r[6]) for r in rows]
    s = base('chart-storm', 330, ml=(46, 54), mr=(14, 16))
    s['X'] = dict(lo=25, hi=210, log=True, ticks=[[v, '%d' % v] for v in (30, 50, 90, 114, 200)], title='LIST cost, seat-seconds, log scale', ntitle='LIST cost (log)')
    s['Y'] = dict(lo=0, hi=4500, ticks=[[v, '%d' % v] for v in (0, 1000, 2000, 3000, 4000)], title='LISTs in hour 8 after the trigger', ntitle='LISTs, hour 8')
    e = s['els']
    e.append(dict(t='line', pts=[[c, 3600 * 100.0 / c] for c in (90, 100, 120, 150, 200)], c='g', w=1, dash=True))
    e.append(dict(t='txt', x=200, y=1800, s='all capacity on LISTs', n='capacity', al='right', bl='top', dx=-4, dy=10, c='g'))
    e.append(dict(t='vline', x=37.5, c='g', dash=True))
    e.append(dict(t='txt', x=37.5, y=4500, s='necessary: 37.5', n='37.5', al='left', bl='top', dx=4, dy=4, c='g'))
    # each series is calm up to its onset and storms after it; nothing was measured in between, so no line crosses the jump
    for series, col in ((ideal, 'a'), (limited, 'b')):
        calm = [[a, b] for a, b in zip(cost, series) if b == 0]
        storm = [[a, b] for a, b in zip(cost, series) if b > 0]
        e.append(dict(t='line', pts=calm, c=col, w=2, mk=3))
        e.append(dict(t='line', pts=storm, c=col, w=2, mk=3))
    on_i = min(c for c, v in zip(cost, ideal) if v > 0)
    on_l = min(c for c, v in zip(cost, limited) if v > 0)
    e.append(dict(t='txt', x=on_i, y=[v for c, v in zip(cost, ideal) if c == on_i][0], s='idealized: %d' % on_i, n='%d' % on_i, al='right', bl='bottom', dx=-6, dy=-4, c='a', b=True))
    e.append(dict(t='txt', x=on_l, y=800, s='documented: %d' % on_l, n='%d' % on_l, al='right', bl='middle', dx=-10, c='b', b=True))
    aria = ('LISTs completed in the eighth hour after a trigger forcing all 2000 informers to LIST, against LIST cost. Idealized queue: %s. With the wait limit and the Reflector backoff: %s. '
            'A saturated storm is impossible below a cost of 37.5.' % (', '.join('%d: %d' % (a, b) for a, b in zip(cost, ideal)), ', '.join('%d: %d' % (a, b) for a, b in zip(cost, limited))))
    cap = ('LISTs still running eight hours after a trigger, against the cost of one LIST. A storm that holds spends all capacity on '
           'LISTs (gray dashed). The idealized queue storms from a cost of 90, the real server, with its wait limit and the client\'s '
           'backoff, from 114, and each line breaks where the count jumps. Below 37.5 no order of service can sustain a storm.')
    FIGS.append(Figure('storm', s, aria, cap))


def fig_second_wave():
    rows = [cells(r) for r in section('T42')]
    cost = [number(r[0]) for r in rows]
    one = [math.fsum(number(x) for x in r[3].split()) / 3 for r in rows]
    fair = [math.fsum(number(x) for x in r[4].split()) / 3 for r in rows]
    s = base('chart-second-wave', 300, ml=(40, 48), mr=(14, 16))
    s['X'] = dict(lo=29.5, hi=40.5, ticks=[[v, '%d' % v] for v in range(30, 41, 2)], title='LIST cost, seat-seconds', ntitle='LIST cost')
    s['Y'] = dict(lo=0, hi=22, ticks=[[v, '%d' % v] for v in (0, 5, 10, 15, 20)], title='re-watches answered 410, mean of three runs', ntitle='410s (mean)')
    e = s['els']
    e.append(dict(t='vline', x=30.0, c='a', dash=True))
    e.append(dict(t='txt', x=30.0, y=22, s='idealized threshold: above 30', n='idealized: 30', al='left', bl='top', dx=4, dy=4, c='a'))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(cost, one)], c='b', w=2, mk=3))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(cost, fair)], c='c', w=2, mk=3, dash=True))
    e.append(dict(t='txt', x=31, y=10, s='one queue, wait limit', n='one queue', al='left', bl='bottom', c='b', b=True))
    e.append(dict(t='txt', x=31, y=8.5, s='fair queuing (dashed)', n='fair (dashed)', al='left', bl='bottom', c='c'))
    aria = ('Re-watches answered 410 in the three hours after a trigger, mean of three runs, against LIST cost. One queue with the wait limit: %s. Fair queuing: %s. '
            'The idealized queue starts a second wave exactly above 30.' % (', '.join('%d: %.1f' % (a, b) for a, b in zip(cost, one)), ', '.join('%d: %.1f' % (a, b) for a, b in zip(cost, fair))))
    cap = ('Where the second wave starts. The idealized queue answers its first re-watch with 410 exactly above a LIST cost of 30, where the forced '
           'backlog outlasts the shortest watch plus the history. With the wait limit and the client\'s backoff the first 410s appear at 31 to 33 '
           'and grow from there, with fair queuing and with one queue alike.')
    FIGS.append(Figure('second-wave', s, aria, cap))


def _pareto_front(points):
    """The points no other point beats on both counts, lower being better, in order of the first."""
    out = []
    for x, y in sorted(points):
        if not out or y < out[-1][1]:
            out.append((x, y))
    return out


def fig_tail_share():
    share = {}
    for r in section('T98'):
        c = cells(r)
        if c[0] == 'share':
            share.setdefault(_n(c[1]), []).append((_n(c[2]), _n(c[3])))
    s = base('chart-tail-share', 320, ml=(40, 48), mr=(14, 16))
    e = s['els']
    e.append(dict(t='vline', x=2000, c='g'))
    e.append(dict(t='txt', x=2000, y=1.04, s='backlog at the boundary on average', n='boundary', al='left', bl='bottom', dx=4, c='g'))
    for a, col in ((3.0, 'g'), (2.0, 'b'), (1.5, 'd'), (1.2, 'a')):
        e.append(dict(t='line', pts=[[k, v] for k, v in share[a]], c=col, mk=3))
    for row, (a, col, note) in enumerate(((3.0, 'g', ', light tail'), (2.0, 'b', ''), (1.5, 'd', ''), (1.2, 'a', ', heavy tail'))):
        e.append(dict(t='txt', x=1000, y=round(0.95 - 0.08 * row, 2), s='exponent %s%s' % (_g(a), note), n='exponent %s' % _g(a),
                      al='left', bl='middle', c=col, b=a == 1.2))
    k, v = share[1.2][0]
    e.append(dict(t='txt', x=k, y=v, s='%.1f%% at half size' % (100 * v), n='', al='left', bl='bottom', dx=4, dy=-6, c='a'))
    s['X'] = dict(lo=900, hi=3100, ticks=[[v, '%d' % v] for v in (1000, 1500, 2000, 2500, 3000)], title='informers in the cluster', ntitle='informers')
    s['Y'] = dict(lo=-0.03, hi=1.08, ticks=[[0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1.0, '100%']],
                  title='share of clusters that storm', ntitle='share storming')
    _id_last(s)

    def curve(pts):
        zeros = [k for k, v in pts if v == 0]
        ones = [k for k, v in pts if v == 1]
        parts = ['0 up to %d' % max(zeros)] if zeros else []
        parts += ['%.3f at %d' % (v, k) for k, v in pts if 0 < v < 1]
        parts += ['1 from %d' % min(ones)] if ones else []
        return ', '.join(parts)
    aria = ('Share of clusters whose full-trigger backlog passes the storm boundary, against the number of informers, for list costs '
            'Pareto with exponents 3, 2, 1.5 and 1.2 and a mean that puts 2,000 informers at the boundary on average. %s.'
            % '. '.join('Exponent %s: %s' % (_g(a), curve(share[a])) for a in (3.0, 2.0, 1.5, 1.2)))
    first = share[1.2][0]
    cap = ('Share of clusters that storm after a full trigger, against their number of informers, with list costs drawn from a Pareto '
           'law. With a light tail the share is a step at the boundary. With a heavy one a cluster\'s few largest collections decide: '
           'at an exponent of 1.2, %.1f%% of half-size clusters storm, and nearly half of those a quarter larger do not.'
           % (100 * first[1]))
    FIGS.append(Figure('tail-share', s, aria, cap))


def fig_hold_frontier():
    hold = {}
    for r in section('T104'):
        c = cells(r)
        if c[0] == 'hold':
            hold.setdefault(int(c[1]), []).append((int(c[2]), _n(c[4]), int(c[3]), c[6] == 'yes'))
    s = base('chart-hold-frontier', 320, ml=(48, 56), mr=(14, 16))
    e = s['els']
    for h, minutes, lost, kept in hold[150]:
        e.append(dict(t='pt', x=minutes, y=lost, r=4, c='b'))
    for h, minutes, lost, kept in hold[200]:
        e.append(dict(t='pt', x=minutes, y=lost, r=5 if kept else 4, c='a', open=kept))
    for cost, col in ((150, 'b'), (200, 'a')):
        front = _pareto_front([(m, n) for _, m, n, kept in hold[cost] if not kept])
        e.append(dict(t='line', pts=[[m, n] for m, n in front], c=col, w=1, dash=True))

    def at(cost, h):
        return [r for r in hold[cost] if r[0] == h][0]
    e.append(dict(t='txt', x=3, y=12500, s='blue: list cost 150', n='blue: 150', al='left', bl='middle', c='b'))
    e.append(dict(t='txt', x=3, y=8800, s='red: list cost 200', n='red: 200', al='left', bl='middle', c='a'))
    _, m, n, _ = at(150, 300)
    e.append(dict(t='txt', x=m, y=n, s='150: hold 300 s, dominated', n='300 s', al='left', bl='top', dx=6, dy=2, c='b'))
    _, m, n, _ = at(200, 300)
    e.append(dict(t='txt', x=m, y=n, s='200: hold 300 s, storm kept', n='300 s: storm', al='right', bl='bottom', dx=-6, dy=-4, c='a', b=True))
    _, m, n, _ = at(200, 0)
    e.append(dict(t='txt', x=m, y=n, s='no hold, storm kept', n='no hold', al='left', bl='middle', dx=8, c='a'))
    _, m, n, _ = at(200, 3600)
    e.append(dict(t='txt', x=m, y=n, s='hold 1 h', n='1 h', al='left', bl='middle', dx=6, c='a'))
    s['X'] = dict(lo=0, hi=230, ticks=[[v, '%d' % v] for v in (0, 60, 120, 180)], title='minutes the lists stay split off', ntitle='minutes split')
    s['Y'] = dict(lo=150, hi=15000, log=True, ticks=[[200, '200'], [1000, '1,000'], [5000, '5,000']],
                  title='re-watches answered 410', ntitle='410s')
    _id_last(s)
    aria = ('Re-watches answered 410 against minutes the controller keeps lists split off, for holds of %s seconds. %s.'
            % (', '.join('%d' % h for h, _, _, _ in hold[150][:-1]) + ' and %d' % hold[150][-1][0],
               '. '.join('List cost %d: %s' % (cost, ', '.join('%.1f min %d%s' % (m, n, ' (storm kept)' if kept else '')
                                                                   for _, m, n, kept in hold[cost])) for cost in (150, 200))))
    cap = ('Each point is one hold, the time the controller keeps lists on their own level after the last 410, at list costs of 150 '
           '(blue) and 200 (red). The dashed lines join the holds no other hold beats on both counts, the controller\'s frontier between '
           'time spent split and re-watches lost. Holds of a few minutes are dominated, and at 200 a hold of 300 seconds, the length of '
           'the history, keeps the storm (open points).')
    FIGS.append(Figure('hold-frontier', s, aria, cap))


# ---------- Part 4 ----------

def fig_placement():
    rows = [cells(r) for r in section('T58')][:3]
    shares = [[number(x) for x in r[1:5]] for r in rows]
    s = base('chart-placement', 300, ml=(40, 48), mr=(14, 16))
    s['X'] = dict(lo=-0.6, hi=3.6, ticks=[[v, '%d' % v] for v in range(4)], title='application replicas lost to one rolling upgrade, of 3', ntitle='replicas lost, of 3')
    s['Y'] = dict(lo=0, hi=0.7, ticks=[[v, _pct(v)] for v in (0, 0.2, 0.4, 0.6)], title='share of drain orders', ntitle='share of orders')
    e = s['els']
    for k, (col, off) in enumerate((('g', -0.27), ('b', 0.0), ('a', 0.27))):
        for j, v in enumerate(shares[k]):
            if v > 0:
                e.append(dict(t='rect', x0=j + off - 0.12, x1=j + off + 0.12, y0=0, y1=v, c=col, al=0.85))
    e.append(dict(t='txt', x=0.55, y=0.68, s='gray: out of reach of later drains', n='gray: out of reach', al='left', bl='top', c='g'))
    e.append(dict(t='txt', x=0.55, y=0.62, s='blue: spread, the default', n='blue: spread', al='left', bl='top', c='b'))
    e.append(dict(t='txt', x=0.55, y=0.56, s='red: packed onto the fullest node', n='red: packed', al='left', bl='top', c='a', b=True))
    names = ('out of reach', 'spread', 'packed')
    aria = ('Share of 20000 rolling-upgrade orders in which the application loses 0, 1, 2 or 3 of its 3 replicas. ' +
            '. '.join('%s: %s' % (n, ', '.join('%d lost %s' % (j, _pct(v)) for j, v in enumerate(sh))) for n, sh in zip(names, shares)) + '.')
    cap = ('What one rolling upgrade takes from an application whose pods need a webhook that rejects its own. With replacements out of reach of '
           'later drains, or spread by the default scorer, the loss is graded. Packed by the most-allocated scorer, the replicas gather on one node not yet '
           'drained, and the application keeps all three or loses all three.')
    FIGS.append(Figure('placement', s, aria, cap))


def fig_cold_start():
    rows = [cells(r) for r in section('T60')]
    dns = [number(r[0]) for r in rows]
    ideal = [number(r[3]) for r in rows]
    real = [number(r[4]) for r in rows]
    s = base('chart-cold-start', 320, ml=(46, 54), mr=(14, 16))
    s['X'] = dict(lo=0, hi=1230, ticks=[[v, '%d' % v] for v in (0, 300, 600, 900, 1200)], title='seconds until DNS is ready after a full restart', ntitle='DNS ready, s')
    s['Y'] = dict(lo=0, hi=1600, ticks=[[v, '%d' % v] for v in (0, 400, 800, 1200, 1600)], title='seconds until the application is ready', ntitle='application ready, s')
    e = s['els']
    e.append(dict(t='line', pts=[[a, min(2 * b, 1600)] for a, b in zip(dns, ideal) if 2 * b <= 1600], c='g', w=1, dash=True))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(dns, ideal)], c='b', w=2))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(dns, real)], c='a', w=2))
    e.append(dict(t='txt', x=560, y=1450, s='twice the instant-retry time (dashed)', n='2 x (dashed)', al='right', bl='bottom', c='g'))
    e.append(dict(t='txt', x=1200, y=1250, s='instant retries', n='instant', al='right', bl='top', dx=-4, dy=22, c='b', b=True))
    e.append(dict(t='txt', x=700, y=1500, s='documented backoffs', n='backoffs', al='left', bl='bottom', dx=6, c='a', b=True))
    pick = [i for i, a in enumerate(dns) if a in (30, 90, 120, 300, 600, 1200)]
    aria = ('Seconds until the application is ready after a full restart, against seconds until DNS is ready, every 15 s from 30 to 1200. '
            'Instant retries and documented backoffs at selected points: ' + ', '.join('%d s: %.0f and %.0f' % (dns[i], ideal[i], real[i]) for i in pick) + '.')
    cap = ('The way back through two backoffs. With instant retries the application follows DNS by a fixed 100 seconds. With the kubelet\'s '
           'restart backoff and the workqueue\'s retry backoff it follows a sawtooth that passes twice that time, nearly three times at worst, and falls back only where '
           'the caps of 300 and 1000 seconds bind.')
    FIGS.append(Figure('cold-start', s, aria, cap))


def fig_percolation():
    share = {}
    for r in section('T100'):
        c = cells(r)
        if c[0] == 'share':
            share.setdefault(c[1], []).append((c[2], _n(c[2]), _n(c[3])))
    s = base('chart-percolation', 320, ml=(40, 48), mr=(14, 16))
    e = s['els']
    e.append(dict(t='vline', x=1.0, c='g'))
    for w, col in (('equal', 'b'), ('Pareto 2.5', 'd'), ('Pareto 1.8', 'a')):
        e.append(dict(t='line', pts=[[x, v] for _, x, v in share[w]], c=col, mk=3))

    def at(w, x):
        return [v for _, cx, v in share[w] if cx == x][0]
    e.append(dict(t='txt', x=1.2, y=at('equal', 1.2), s='independent degrees', n='independent', al='left', bl='top', dx=6, dy=2, c='b'))
    e.append(dict(t='txt', x=1.5, y=at('Pareto 2.5', 1.5), s='hubs, exponent 2.5', n='2.5', al='right', bl='bottom', dx=-8, dy=-6, c='d'))
    e.append(dict(t='txt', x=0.5, y=at('Pareto 1.8', 0.5), s='hubs, exponent 1.8', n='1.8', al='right', bl='bottom', dx=-6, dy=-4, c='a', b=True))
    e.append(dict(t='txt', x=1.0, y=0.95, s='one need per component', n='', al='left', bl='middle', dx=4, c='g'))
    s['X'] = dict(lo=0.15, hi=2.05, ticks=[[0.5, '0.5'], [1.0, '1'], [1.5, '1.5'], [2.0, '2']],
                  title='mean start-time needs per component', ntitle='mean needs')
    s['Y'] = dict(lo=-0.02, hi=1.0, ticks=[[0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%']],
                  title='share stranded after a full restart', ntitle='share stranded')
    _id_last(s)

    def val(v):
        return '0' if v == 0 else '%.3f' % v
    aria = ('Share of 1,000 components stranded after a full restart against the mean number of start-time needs per component. '
            'Independent degrees: %s. Hubs, Pareto weights of exponent 2.5: %s. Hubs, exponent 1.8: %s.'
            % (', '.join('%s: %s' % (t, val(v)) for t, _, v in share['equal']), ', '.join(val(v) for _, _, v in share['Pareto 2.5']),
               ', '.join(val(v) for _, _, v in share['Pareto 1.8'])))
    a = 2.5
    limit = a * (a - 2) / (a - 1) ** 2   # E[w]^2 / E[w^2] for Pareto weights: the threshold in the limit of many components
    cap = ('Share of components that never start after a full restart, against the mean number of components each one needs, for random '
           'start-time graphs of 1,000 components, the mean of 30 draws. With independent degrees the stranded set appears near one need per component. With '
           'hubs whose needs and dependents grow together it appears earlier, near the predicted %.2f for weights of exponent 2.5, and '
           'almost at once for exponent 1.8, whose weights have no second moment.' % limit)
    FIGS.append(Figure('percolation', s, aria, cap))


def fig_relaxation_cliff():
    relax = {}
    for r in section('T104'):
        c = cells(r)
        if c[0] == 'relax':
            relax.setdefault(c[1], []).append((int(c[2]), int(c[3])))
    s = base('chart-relaxation-cliff', 300, ml=(40, 48), mr=(14, 16))
    e = s['els']
    e.append(dict(t='line', pts=[[k, n] for k, n in relax['equal']], c='b', mk=3))
    e.append(dict(t='line', pts=[[k, n] for k, n in relax['Pareto 1.8']], c='a', mk=3))
    eq, hub = dict(relax['equal']), dict(relax['Pareto 1.8'])
    keq, khub = max(eq), max(hub)
    e.append(dict(t='txt', x=48, y=eq[48], s='independent: %d left after 48 of %d' % (eq[48], keq), n='48 of %d: %d' % (keq, eq[48]),
                  al='right', bl='top', dx=-6, dy=10, c='b'))
    e.append(dict(t='txt', x=32, y=hub[32], s='hubs: %d left after 32 of %d' % (hub[32], khub), n='32 of %d: %d' % (khub, hub[32]),
                  al='right', bl='top', dx=-6, dy=6, c='a', b=True))
    s['X'] = dict(lo=-1, hi=66, ticks=[[v, '%d' % v] for v in (0, 16, 32, 48, 64)], title="components relaxed, in the controller's order", ntitle='relaxed')
    s['Y'] = dict(lo=-20, hi=800, ticks=[[v, '%d' % v] for v in (0, 200, 400, 600, 800)], title='components still stranded, of 1,000', ntitle='stranded')
    _id_last(s)
    aria = ("Components still stranded after relaxing the first k components of the controller's relaxation, at two needs per component. "
            'Independent degrees: %s. Hubs, Pareto 1.8: %s.'
            % (', '.join('%d: %d' % p for p in relax['equal']), ', '.join('%d: %d' % p for p in relax['Pareto 1.8'])))
    cap = ('Components still stranded as the controller relaxes the components of its set one at a time, in the order it chose them, on one drawn graph of 1,000 components for each kind of degree. '
           'With independent degrees the first 48 of %d relaxations free %d of %d components, and the last two free %d. With hubs the '
           'curve is gentler, and the last relaxation still frees %d. A relaxation pays when it is complete, which is why one unseen edge '
           'undoes it.' % (keq, eq[0] - eq[48], eq[0], eq[keq - 2], hub[khub - 1]))
    FIGS.append(Figure('relaxation-cliff', s, aria, cap))


def fig_relaxation_limits():
    rows_ = {}
    total = {}
    for r in section('T101'):
        c = cells(r)
        if c[0] in ('hidden', 'hard') and c[2] == '2.0':
            share = float(c[3])
            rows_.setdefault((c[0], c[1]), []).append(('0' if share == 0 else c[3], 0 if share == 0 else share, int(c[4])))
        if c[0] == 'relax' and c[2] == '2.0':
            total[c[1]] = int(c[3])
    s = base('chart-relaxation-limits', 320, ml=(40, 48), mr=(14, 16))
    e = s['els']
    for kind, w, col, dash in (('hidden', 'equal', 'b', False), ('hidden', 'Pareto 1.8', 'a', False),
                               ('hard', 'equal', 'b', True), ('hard', 'Pareto 1.8', 'a', True)):
        el = dict(t='line', pts=[[x, n] for _, x, n in rows_[(kind, w)]], c=col, mk=3)
        if dash:
            el['dash'] = True
        e.append(el)

    def last(kind, w):
        return rows_[(kind, w)][-1]
    _, x, n = last('hidden', 'equal')
    e.append(dict(t='txt', x=x, y=n, s='unseen edges, independent', n='unseen, indep.', al='left', bl='middle', dx=6, c='b'))
    _, x, n = last('hidden', 'Pareto 1.8')
    e.append(dict(t='txt', x=x, y=n, s='unseen edges, hubs', n='unseen, hubs', al='left', bl='middle', dx=6, c='a', b=True))
    _, x, n = last('hard', 'Pareto 1.8')
    e.append(dict(t='txt', x=x, y=n, s='hard edges, hubs', n='hard, hubs', al='right', bl='bottom', dx=-4, dy=-6, c='a'))
    _, x, n = last('hard', 'equal')
    e.append(dict(t='txt', x=x, y=n, s='hard edges, independent', n='hard, indep.', al='right', bl='bottom', dx=-4, dy=-6, c='b'))
    s['X'] = dict(lo=-0.01, hi=0.52, ticks=[[0, '0']] + [[v, _pct(v)] for v in (0.1, 0.2, 0.3, 0.4, 0.5)],
                  title='share of edges unseen (solid) or unrelaxable (dashed)', ntitle='share of edges')
    s['Y'] = dict(lo=-20, hi=800, ticks=[[v, '%d' % v] for v in (0, 200, 400, 600, 800)], title='components still stranded, of 1,000', ntitle='still stranded')
    _id_last(s)
    aria = ("Components still stranded after the controller's relaxation, of 1,000 at a mean of two needs per component, against a share "
            'of edges. Edges the controller cannot see, independent degrees: %s of %d. Same, hubs of exponent 1.8: %s of %d. Edges that '
            'cannot be relaxed, independent degrees: %s. Same, hubs: %s.'
            % (', '.join('%s: %d' % (t, n) for t, _, n in rows_[('hidden', 'equal')]), total['equal'],
               ', '.join('%d' % n for _, _, n in rows_[('hidden', 'Pareto 1.8')]), total['Pareto 1.8'],
               ', '.join('%s: %d' % (t, n) for t, _, n in rows_[('hard', 'equal')]),
               ', '.join('%d' % n for _, _, n in rows_[('hard', 'Pareto 1.8')])))
    cap = ('Components still stranded after the recovery controller acts, at two needs per component, on one drawn graph for each kind of degree. Solid lines: edges missing from '
           'the graph it plans on, where 5% missing leaves most of the stranded set in place. Dashed lines: edges nobody can relax, '
           'which leave a floor, zero until half the edges with independent degrees, rising from a tenth with hubs.')
    FIGS.append(Figure('relaxation-limits', s, aria, cap))


# ---------- Part 5 ----------

def fig_chain_share():
    rows = [cells(r) for r in section('T16')]
    n = [number(r[0]) for r in rows]
    two = [number(r[2]) for r in rows]
    one = [number(r[4]) for r in rows]
    s = base('chart-chain-share', 300, ml=(46, 54), mr=(14, 16))
    s['X'] = dict(lo=1.8, hi=6.2, ticks=[[v, '%d' % v] for v in range(2, 7)], title='webhooks in an enabling chain', ntitle='chain length')
    s['Y'] = dict(lo=0.001, hi=1.2, log=True, ticks=[[1, '100%'], [0.1, '10%'], [0.01, '1%'], [0.001, '0.1%']], title='share of orders that reach the common fixed point (log scale)', ntitle='share converging (log)')
    e = s['els']
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(n, two)], c='b', w=2, mk=3))
    e.append(dict(t='line', pts=[[a, b] for a, b in zip(n, one)], c='a', w=2, mk=3))
    e.append(dict(t='txt', x=4.1, y=0.62, s='value links, opted in, two passes', n='opted in, 2 passes', al='left', bl='bottom', c='b', b=True))
    e.append(dict(t='txt', x=3.6, y=0.025, s='run once, or match links: 1/n!', n='run once, or match links', al='right', bl='top', c='a', b=True))
    aria = ('Share of orders of an enabling chain of n webhooks that reach the common fixed point. Value links, opted in, two passes: ' +
            ', '.join('%d: %.4f' % (a, b) for a, b in zip(n, two)) + '. Value links whose members run once, and match links at any number of passes: ' +
            ', '.join('%d: %.4f' % (a, b) for a, b in zip(n, one)) + '.')
    cap = ('What the second pass buys and what a match link takes away. With every webhook opted in, two passes keep a chain of value links '
           'converging in a share of orders that falls slowly at first; when they run once only the order with every enabler first converges, one in n!. '
           'A chain of match links falls to that same curve at any number of passes, because a webhook skipped in the first pass is never called.')
    FIGS.append(Figure('chain-share', s, aria, cap))


def fig_position_share():
    """T82: under the contract's two passes, the share of orders that converge against the position of the last member
    that runs once (or, by Proposition 30, of the last match link), for chains of four to six, with the share that
    passes enough would give."""
    by = {}
    ceiling = {}
    for r in section('T82'):
        c = cells(r)
        n, eta, two, cap_ = int(c[0]), int(c[1]), _n(c[2]), _n(c[4])
        by.setdefault(n, []).append((eta, two))
        ceiling[eta] = cap_
    s = base('chart-position-share', 320, ml=(46, 54), mr=(14, 16))
    e = s['els']
    e.append(dict(t='line', pts=[[k, v] for k, v in sorted(ceiling.items())], c='g', w=1.5, dash=True))
    for n, col in ((4, 'c'), (5, 'b'), (6, 'a')):
        e.append(dict(t='line', pts=[[k, v] for k, v in by[n]], c=col, mk=3))
    # a legend in the empty upper right, where every curve is below 5%
    e.append(dict(t='txt', x=3.1, y=0.72, s='dashed: passes enough, 1 / (position + 1)!', n='dashed: passes enough', al='left', bl='middle', c='g'))
    for row, (n, col) in enumerate(((4, 'c'), (5, 'b'), (6, 'a'))):
        e.append(dict(t='txt', x=3.1, y=(0.42, 0.25, 0.15)[row], s='%d webhooks, two passes' % n, n='%d webhooks' % n, al='left', bl='middle',
                      c=col, b=n == 6))
    s['X'] = dict(lo=-0.25, hi=5.25, ticks=[[k, '%d' % k] for k in range(6)],
                  title='position of the last webhook that runs once, or of the last match link', ntitle='position of the last once member')
    s['Y'] = dict(lo=0.001, hi=1.3, log=True, ticks=[[1, '100%'], [0.1, '10%'], [0.01, '1%'], [0.001, '0.1%']],
                  title='share of orders that converge (log scale)', ntitle='converging (log)')
    _id_last(s)
    aria = ('Share of orders of a chain of value links that converge under two passes, against the position of the last member that runs '
            'once, counting the first as 0. %s. With passes enough: %s.'
            % ('; '.join('%d webhooks: %s' % (n, ', '.join('%d: %.4f' % kv for kv in by[n])) for n in (4, 5, 6)),
               ', '.join('%d: %.4f' % kv for kv in sorted(ceiling.items()))))
    cap = ('Where in the chain the default does its damage. A member that runs once fails as a match link fails, so every member up to it '
           'must stand in chain order. The later it sits, the fewer orders converge, and under the contract\'s two passes a long chain '
           'falls below the dashed share that passes enough would give. The two meet once at most one value link follows the member.')
    FIGS.append(Figure('position-share', s, aria, cap))

def fig_passes_frontier():
    front = {}
    for r in section('T102'):
        c = cells(r)
        if c[0] == 'frontier':
            front.setdefault(int(c[1]), []).append((int(c[2]), _n(c[3])))
    s = base('chart-passes-frontier', 320, ml=(40, 48), mr=(14, 16))
    e = s['els']
    e.append(dict(t='vline', x=2, c='g'))
    e.append(dict(t='txt', x=2, y=1.06, s="the contract's two passes", n='two passes', al='left', bl='middle', dx=4, c='g'))
    for n, col in ((3, 'g'), (4, 'c'), (5, 'b'), (6, 'd'), (7, 'a')):
        e.append(dict(t='line', pts=[[k, v] for k, v in front[n]], c=col, mk=3))
    two3, two7 = dict(front[3])[2], dict(front[7])[2]
    for row, (n, col) in enumerate(((3, 'g'), (4, 'c'), (5, 'b'), (6, 'd'), (7, 'a'))):
        e.append(dict(t='txt', x=5.3, y=round(0.62 - 0.1 * row, 2), s='%d webhooks' % n, n='%d webhooks' % n if n == 3 else '%d' % n, al='left', bl='middle', c=col, b=n == 7))
    e.append(dict(t='txt', x=2, y=two7, s='7 webhooks: %.1f%%' % (100 * two7), n='7: %.1f%%' % (100 * two7), al='left', bl='bottom', dx=6, dy=-2, c='a', b=True))
    s['X'] = dict(lo=0.8, hi=7.2, ticks=[[k, '%d' % k] for k in range(1, 8)], title='passes allowed', ntitle='passes')
    s['Y'] = dict(lo=-0.03, hi=1.1, ticks=[[0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1.0, '100%']],
                  title='share of orders that converge', ntitle='converged')
    _id_last(s)
    first = '3 webhooks: ' + ', '.join('%d pass%s %s' % (k, '' if k == 1 else 'es', _g(v)) for k, v in front[3])
    rest = ['%d: %s' % (n, ', '.join(_g(v) for _, v in front[n])) for n in (4, 5, 6, 7)]
    aria = ('Share of orders of an enabling chain of value links that reach the common fixed point within P passes. %s.'
            % '. '.join([first] + rest))
    cap = ('Share of orders of an enabling chain that converge within a number of passes, for chains of three to seven webhooks. Each '
           'line rises from almost none to all as the passes grow, and the rise moves right by half a pass for each webhook added. The '
           'contract fixes the passes at two, where the share falls from %d%% at three webhooks to %.1f%% at seven.'
           % (round(100 * two3), 100 * two7))
    FIGS.append(Figure('passes-frontier', s, aria, cap))


# ---------- Part 6 ----------

def fig_pairwise_misses():
    rows = [cells(r) for r in section('T73')]
    order = [(number(r[1]), number(r[3])) for r in rows if r[0] == 'order']
    assume = [(number(r[1]), number(r[4])) for r in rows if r[0] == 'assumption' and abs(number(r[2]) - 0.2) < 1e-9]
    signal = [(number(r[1]), number(r[5])) for r in rows if r[0] == 'signal' and abs(number(r[2]) - 0.8) < 1e-9]
    s = base('chart-pairwise-misses', 300, ml=(40, 48), mr=(14, 16))
    s['X'] = dict(lo=2.7, hi=6.3, ticks=[[v, '%d' % v] for v in range(3, 7)], title='mechanisms in the set', ntitle='mechanisms')
    s['Y'] = dict(lo=0, hi=1.12, ticks=[[0, '0%'], [0.25, '25%'], [0.5, '50%'], [0.75, '75%'], [1.0, '100%']], title='share of failing systems that every pair passes', ntitle='every pair passes')
    e = s['els']
    e.append(dict(t='line', pts=[[a, b] for a, b in order], c='a', w=2, mk=3))
    e.append(dict(t='line', pts=[[a, b] for a, b in signal], c='b', w=2, mk=3))
    e.append(dict(t='line', pts=[[a, b] for a, b in assume], c='c', w=2, mk=3))
    e.append(dict(t='txt', x=order[-1][0], y=order[-1][1], s='order: every pair needs 2 passes or fewer', n='order', al='right', bl='bottom', dx=-6, dy=-8, c='a', b=True))
    e.append(dict(t='txt', x=signal[-1][0], y=signal[-1][1], s='signal: no pair reversed, every pair below 2', n='signal', al='right', bl='top', dx=-6, dy=8, c='b', b=True))
    e.append(dict(t='txt', x=assume[-1][0], y=assume[-1][1], s='assumption: no pair needs each other', n='assumption', al='right', bl='bottom', dx=-6, dy=-8, c='c', b=True))
    aria = ('Share of failing random systems that a check of every pair passes, against the number of mechanisms. Order, random fact graphs: ' +
            ', '.join('%d: %.4f' % (a, b) for a, b in order) + '. Signal, couplings within 0.8, reversed loops with every pair below 2: ' +
            ', '.join('%d: %.4f' % (a, b) for a, b in signal) + '. Assumption, start-time graphs at probability 0.2 with no self-matching: ' +
            ', '.join('%d: %.4f' % (a, b) for a, b in assume) + '.')
    cap = ('How often a failure is one no pair shows, in random systems. Failing webhook orders almost always pass every pairwise check, '
           'because a chain of depth two needs three webhooks. Reversed loops never show a reversal in any pair, and most read close to independent. '
           'Start-time cycles are the most forgiving: most contain two components that need each other, which a pairwise check finds.')
    FIGS.append(Figure('pairwise-misses', s, aria, cap))


def fig_seam_ratios():
    rows_ = [cells(r) for r in section('T112')]

    def pick(kind):
        return [r for r in rows_ if r[0] == kind]
    s = base('chart-seam-ratios', 320, ml=(34, 44), mr=(14, 16))
    s['X'] = dict(lo=0.5, hi=5.6, ticks=[[1, 'signal'], [2, 'time scale'], [3, 'state'], [4, 'order'], [5, 'assumption']],
                  title='seam', ntitle='seam')
    s['Y'] = dict(lo=0, hi=4.3, ticks=[[v, '%d' % v] for v in range(5)], title='seam ratio', ntitle='ratio')
    e = s['els']
    e.append(dict(t='hline', y=1.0, c='g', w=1, dash=True))
    e.append(dict(t='txt', x=5.45, y=1.0, s='binds above one', n='binds', al='right', bl='top', dy=7, c='g'))
    signal = [(r[1], _n(r[2])) for r in pick('signal') if r[1] != '0.95']
    time = [(int(r[1]), _n(r[3])) for r in pick('time')]
    state = {(int(r[1]), int(r[2])): _n(r[3]) for r in pick('state')}
    state = [('list cost 120', state[(2000, 120)]), ('100', state[(2000, 100)]), ('750 informers', state[(750, 100)])]
    order = [_n(r[3]) for r in pick('order')]
    assume = [_n(r[2]) for r in pick('assumption')]
    short = {'no slots': '0', '112 slots': '112', 'list cost 120': '120', '750 informers': '750 inf.', 'configured order': 'as named',
             'surveyed defaults': 'defaults', 'Kyverno fails open': 'Kyverno open'}
    points = ([(1, ('target ' if i == 0 else '') + _g(float(t)), v, v > 1) for i, (t, v) in enumerate(signal)]
              + [(2, 'no slots' if k == 0 else ('%d slots' % k if i == len(time) - 1 else '%d' % k), v, v > 1) for i, (k, v) in enumerate(time)]
              + [(3, lab, v, v > 1) for lab, v in state]
              + [(4, 'configured order', order[0], order[0] > 1), (4, 'renamed', order[1], order[1] > 1)]
              + [(5, 'surveyed defaults', assume[0], assume[0] >= 1), (5, 'Kyverno fails open', assume[1], assume[1] >= 1)])
    # the targets 0.8 and 0.9 lie a few pixels apart: one label, to the left of both
    close = [p for p in points if p[0] == 1 and p[1] in ('0.8', '0.9')]
    for x, lab, v, binds in points:
        e.append(dict(t='pt', x=x, y=v, r=4, c='a' if binds else 'c'))
        if lab == '0.9':
            continue
        on_line = v in (0, 1)   # a label at the dashed line or the axis sits above its point
        if lab == '0.8':
            e.append(dict(t='txt', x=x, y=min(p[2] for p in close), s='0.8, 0.9', n='0.8, 0.9', al='left', bl='top', dx=7, dy=2, c='sub'))
        elif x == 5:
            e.append(dict(t='txt', x=x, y=v, s=lab, n=short.get(lab, lab), al='right', bl='bottom' if on_line else 'middle', dx=-7, dy=-3 if on_line else 0, c='sub'))
        else:
            e.append(dict(t='txt', x=x, y=v, s=lab, n=short.get(lab, lab.replace('target ', '')), al='left', bl='bottom' if on_line else 'middle',
                          dx=7, dy=-3 if on_line else 0, c='sub'))
    _axes_first(s)

    def val(v):
        return '0' if v == 0 else repr(v)
    aria = ('Seam ratios of the specimens, binding above one. Signal: target %s. Time scale, thirtyfold surge from 16 pods: no slots %s, '
            '%d slots %s, %s. State: list cost 120: %s, 100: %s, 750 informers at 100: %s. Order: configured order %s, renamed %s. '
            'Assumption: surveyed defaults %s, Kyverno failing open %s.'
            % (', '.join('%s: %s' % (_g(float(t)), val(v)) for t, v in signal), val(time[0][1]), time[1][0], val(time[1][1]),
               ', '.join('%d: %s' % (k, val(v)) for k, v in time[2:]), val(state[0][1]), val(state[1][1]), val(state[2][1]),
               val(order[0]), val(order[1]), val(assume[0]), val(assume[1])))
    cap = ("Each seam's ratio on the specimens of the earlier parts, one point per setting. Points above the dashed line bind. The "
           'assumption binds at one itself, since a single start-time cycle has a radius of exactly one. A fix moves a point down within '
           'its seam, and can move the points of other seams that share its settings.')
    FIGS.append(Figure('seam-ratios', s, aria, cap))


def fig_cross_frontier():
    target, matched, load = [], [], None
    for r in section('T109'):
        c = cells(r)
        if c[0] == 'target':
            target.append((c[1], _z(_n(c[3])), int(c[4])))
        elif c[0] == 'matched':
            matched.append((c[1], int(c[4])))
        elif c[0] == 'load':
            load = (_z(_n(c[1])), int(c[2]))
    drifting = sorted([t for t in target if t[1] > 0], key=lambda t: t[1])
    in_band = [t for t in target if t[1] == 0]
    seconds = []
    for _, sec in matched:
        if sec not in seconds:
            seconds.append(sec)
    s = base('chart-cross-frontier', 320, ml=(40, 48), mr=(14, 16))
    s['X'] = dict(lo=-1.5, hi=20, ticks=[[v, '%d' % v] for v in (0, 5, 10, 15, 20)], title='drift, doublings per 1,000 hours', ntitle='drift')
    s['Y'] = dict(lo=0, hi=8000, ticks=[[0, '0'], [2000, '2,000'], [4000, '4,000'], [6000, '6,000'], [8000, '8,000']],
                  title='seconds until capacity meets a 30x surge', ntitle='surge, s')
    e = s['els']
    front = _pareto_front([(d, sec) for _, d, sec in target] + [(0, sec) for sec in seconds])
    e.append(dict(t='line', pts=[[d, sec] for d, sec in front], c='g', w=1, dash=True))
    e.append(dict(t='line', pts=[[d, sec] for _, d, sec in drifting], c='a', w=2, mk=3))
    for _, d, sec in in_band:
        e.append(dict(t='pt', x=d, y=sec, c='a', open=True))
    e.append(dict(t='line', pts=[[0, sec] for sec in seconds], c='b', w=2, mk=3))
    e.append(dict(t='pt', x=load[0], y=load[1], c='c', r=5))
    mid = [t for t in drifting if t[0] == '0.50'][0]
    e.append(dict(t='txt', x=mid[1], y=mid[2], s='target %s to %s, drifting' % (_g(float(mid[0])), _g(float(drifting[-1][0]))), n='drifting',
                  al='left', bl='bottom', dx=6, dy=-6, c='a', b=True))
    e.append(dict(t='txt', x=drifting[0][1], y=drifting[0][2], s='target %s' % _g(float(drifting[0][0])), n=_g(float(drifting[0][0])),
                  al='right', bl='middle', dx=-8, c='a'))
    e.append(dict(t='txt', x=0, y=in_band[-1][2], s='target moved into the band, %s to %s' % (_g(float(in_band[0][0])), _g(float(in_band[-1][0]))),
                  n='target in band', al='left', bl='middle', dx=10, c='a'))
    floor = seconds[0]
    upto = max(float(t) for t, sec in matched if sec == floor)
    beside = seconds[-2]   # above the drifting line, which starts at 2,490 s
    e.append(dict(t='txt', x=0, y=beside, s='matched tolerance: no drift, %s s at best (targets up to %s)' % (format(floor, ','), _g(upto)),
                  n='matched: %s s at best' % format(floor, ','), al='left', bl='middle', dx=10, c='b', b=True))
    e.append(dict(t='txt', x=load[0], y=load[1], s='load metric, %d s' % load[1], n='load metric', al='left', bl='middle', dx=10, c='c', b=True))
    _axes_first(s)
    groups = []
    for t, sec in matched:
        if groups and groups[-1][2] == sec:
            groups[-1][1] = t
        else:
            groups.append([t, t, sec])
    zero = []
    for i, (a, b, sec) in enumerate(groups):
        if a != b:
            zero.append('matched tolerance at targets %s to %s, %d s' % (_g(float(a)), _g(float(b)), sec))
        else:
            zero.append('%s, %d' % (_g(float(a)), sec))
    aria = ('Drift in doublings per 1,000 hours against seconds until capacity meets a 30x surge. Drifting targets %s: %s. Zero drift: %s. '
            'Target moved into the band: %s. Load metric: zero drift, %d s.'
            % (', '.join(_g(float(t)) for t, _, _ in drifting),
               ', '.join('%s and %d%s' % (d, sec, ' s' if i == 0 else '') for i, (_, d, sec) in enumerate(drifting)),
               '; '.join(zero), '; '.join('%s, %d' % (_g(float(t)), sec) for t, _, sec in in_band), load[1]))
    cap = ('Fixes for the shared signal, placed by what they cost a 30x surge. Drifting targets (red) trade drift for speed. Every '
           'fix that stops the drift on the utilization metric sits at zero drift: the matched tolerance (blue) is never faster than '
           '%s seconds, and a target moved into the band (red, open) is slower still. The dashed line is the best that metric allows; '
           'only a load metric (green) has neither drift nor delay.' % format(floor, ','))
    FIGS.append(Figure('cross-frontier', s, aria, cap))


def fig_share_onset():
    rows_ = [cells(r) for r in section('T110')]
    pts = [(int(c[0]), int(c[2]), int(c[3])) for c in rows_]
    whole = [c for c in rows_ if c[0] == '245'][0]
    s = base('chart-share-onset', 300, ml=(40, 48), mr=(14, 16))
    s['X'] = dict(lo=0, hi=245, ticks=[[0, '0'], [30, '30'], [70, '70'], [122.5, '122.5'], [245, '245']],
                  title="the list level's shares, of 245", ntitle='shares')
    s['Y'] = dict(lo=0, hi=120, ticks=[[v, '%d' % v] for v in (0, 30, 60, 90, 120)], title="list cost at the storm's onset", ntitle='onset')
    e = s['els']
    e.append(dict(t='line', pts=[[0, 0], [245, float(whole[4])]], c='g', w=1, dash=True))
    e.append(dict(t='line', pts=[[sh, cost] for sh, cost, _ in pts], c='b', w=2, mk=3))
    e.append(dict(t='vline', x=30, c='a'))
    e.append(dict(t='vline', x=70, c='d'))
    e.append(dict(t='txt', x=30, y=110, s='system, as configured', n='default', al='left', bl='top', dx=4, c='a', b=True))
    e.append(dict(t='txt', x=70, y=92, s='system and node-high merged', n='merged', al='left', bl='top', dx=4, c='d', b=True))
    top = int(whole[2])
    e.append(dict(t='txt', x=245, y=top, s='whole server, %d' % top, n='%d' % top, al='right', bl='bottom', dx=-4, dy=-6, c='b'))
    _axes_first(s)
    lo, hi = min(b for _, _, b in pts), max(b for _, _, b in pts)
    aria = ('Storm onset list cost against shares of 245: %s. Backlog at onset %d to %d s.'
            % (', '.join('%d: %d' % (sh, cost) for sh, cost, _ in pts), lo, hi))
    onset = {sh: cost for sh, cost, _ in pts}
    cap = ("The list cost at which a sudden trigger leaves a storm still running in the eighth hour, against the share of the server the "
           "kubelets' lists are given. Every point sits at the same forced backlog, %s to %s seconds, so the onset falls on the dashed line "
           "through the whole server's %d. The default level holds 30 shares and storms from %d; merged with the heartbeats' level it "
           'holds 70 and storms from %d.' % (format(lo, ','), format(hi, ','), top, onset[30], onset[70]))
    FIGS.append(Figure('share-onset', s, aria, cap))


BUILDERS = [fig_rest_band, fig_drift, fig_settings, fig_tail_regimes, fig_coupling,
            fig_nested, fig_node_time, fig_headroom, fig_second_surge, fig_unneeded, fig_memoryless, fig_worst_gap, fig_pod_memory,
            fig_hazard, fig_surge_tail, fig_cover_frontier, fig_tail_controller,
            fig_storm, fig_second_wave, fig_tail_share, fig_hold_frontier,
            fig_placement, fig_cold_start, fig_percolation, fig_relaxation_cliff, fig_relaxation_limits,
            fig_chain_share, fig_position_share, fig_passes_frontier,
            fig_pairwise_misses, fig_seam_ratios, fig_cross_frontier, fig_share_onset]


def figures(results_path):
    """Build every figure from the results file at results_path, in a fixed order."""
    RESULTS.clear()
    RESULTS.update(read(results_path))
    FIGS.clear()
    for build in BUILDERS:
        build()
    return list(FIGS)
