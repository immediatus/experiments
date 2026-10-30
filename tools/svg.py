"""SVG backend: draws a figspec specification as a standalone SVG document.

The layout mirrors the canvas engine the posts use, at its wide setting: the same margins,
scales, ticks, titles and elements, so a figure in the repository and the same figure in a
post are one drawing. Colours are CSS classes with a light palette and a dark one under
prefers-color-scheme; an opaque background in the same palette keeps text readable whatever
page the image sits on. Coordinates are written with two decimals, so output is byte-stable.

A specification is a dict: id, h (height), ml and mr (left and right margins, narrow and
wide), mt and mb (top and bottom margins), axes X, Y and optional R (lo, hi, log, ticks,
title, col), and els, a list of elements, each with a type t:

  hband y0 y1 | rect x0 x1 y0 y1 | vline x | hline y w | band pts=[[x, lo, hi]] edge |
  line pts=[[x, y]] w mk open | pt x y r open | txt x y s n al bl dx dy b

and the optional keys c (colour: ink sub grid a b c d e g), al (opacity), dash, ax ('R' for
the right axis). n is the canvas backend's narrow-screen label and is ignored here.

  render(fig, width=700) -> str
"""
from __future__ import annotations

import html
import math
from collections import namedtuple

Figure = namedtuple('Figure', 'name spec aria caption')

LIGHT = dict(ink='#333', sub='#555', grid='#d6d6d6', a='#b71c1c', b='#1565c0', c='#2e7d32', d='#e65100', e='#6a1b9a', g='#777', bg='#fff')
DARK = dict(ink='#ddd', sub='#aaa', grid='#444', a='#ef9a9a', b='#8ab4f8', c='#81c784', d='#ffcc80', e='#ce93d8', g='#bbb', bg='#1e1e1e')
ANCHOR = {'left': 'start', 'center': 'middle', 'right': 'end'}
FONT = 11
# Canvas text baselines as fixed offsets from the anchor, in units of the font size, so the
# result does not depend on how a viewer implements dominant-baseline.
BASELINE = {'top': 0.8, 'middle': 0.35, 'bottom': -0.2}
DASH = ' stroke-dasharray="5 4"'


def _css(palette: dict) -> str:
    rules = []
    for k, v in palette.items():
        rules.append('.f-%s{fill:%s}.s-%s{stroke:%s}' % (k, v, k, v))
    return ''.join(rules)


def _f(v: float) -> str:
    return '%.2f' % v


def title(fig: Figure) -> str:
    """A readable title: the first sentence of the caption, or the figure's name without one."""
    first = fig.caption.split('. ', 1)[0].strip().rstrip('.')
    return first or fig.name


def render(fig: Figure, width: int = 700) -> str:
    """A complete SVG document for one figure specification, drawn at the given width."""
    S = fig.spec
    W, H = width, S['h']
    L, R, T, B = S['ml'][1], S['mr'][1], S['mt'], S['mb']
    pw, ph = W - L - R, H - T - B

    def sc(a, v):
        if a.get('log'):
            return (math.log(v) - math.log(a['lo'])) / (math.log(a['hi']) - math.log(a['lo']))
        return (v - a['lo']) / (a['hi'] - a['lo'])

    def X(v):
        return L + pw * sc(S['X'], v)

    def Y(v, k='L'):
        return T + ph * (1 - sc(S['R'] if k == 'R' else S['Y'], v))

    out = []

    def text(s, x, y, al='left', bl='middle', col='ink', bold=False):
        out.append('<text x="%s" y="%s" text-anchor="%s" class="f-%s"%s>%s</text>' % (
            _f(round(x)), _f(round(y) + BASELINE[bl or 'middle'] * FONT), ANCHOR[al or 'left'], col if col in LIGHT else 'ink',
            ' font-weight="bold"' if bold else '', html.escape(s, quote=False)))

    def path(pts):
        return 'M' + ' L'.join('%s %s' % (_f(x), _f(y)) for x, y in pts)

    out.append('<rect x="0" y="0" width="%d" height="%d" class="f-bg"/>' % (W, H))
    for v, lab in S['Y']['ticks']:
        y = round(Y(v)) + 0.5
        out.append('<path d="M%s %s H%s" class="s-grid" fill="none"/>' % (_f(L), _f(y), _f(L + pw)))
        text(lab, L - 5, y, 'right', 'middle', S['Y'].get('col', 'sub'))
    if S.get('R'):
        for v, lab in S['R']['ticks']:
            text(lab, L + pw + 5, Y(v, 'R'), 'left', 'middle', S['R'].get('col', 'sub'))
    for v, lab in S['X']['ticks']:
        s = sc(S['X'], v)
        text(lab, X(v), T + ph + 6, 'left' if s < 0.01 else ('right' if s > 0.99 else 'center'), 'top', 'sub')
    out.append('<path d="M%s %s H%s" class="s-sub" fill="none"/>' % (_f(L), _f(T + ph + 0.5), _f(L + pw)))
    text(S['Y']['title'], L, 4, 'left', 'top', S['Y'].get('col', 'ink'))
    if S.get('R'):
        text(S['R']['title'], L + pw, 4, 'right', 'top', S['R'].get('col', 'ink'))
    text(S['X']['title'], L + pw, H - 2, 'right', 'bottom', 'ink')

    for e in S['els']:
        k, c, t = e.get('ax', 'L'), e.get('c', 'ink'), e['t']
        c = c if c in LIGHT else 'ink'
        dash = DASH if e.get('dash') else ''
        if t == 'hband':
            y0, y1 = Y(e['y0'], k), Y(e['y1'], k)
            out.append('<rect x="%s" y="%s" width="%s" height="%s" class="f-%s" fill-opacity="%s"/>' % (
                _f(L), _f(min(y0, y1)), _f(pw), _f(abs(y1 - y0)), c, e.get('al', 0.12)))
        elif t == 'rect':
            x0, x1, y0, y1 = X(e['x0']), X(e['x1']), Y(e['y0'], k), Y(e['y1'], k)
            out.append('<rect x="%s" y="%s" width="%s" height="%s" class="f-%s" fill-opacity="%s"/>' % (
                _f(min(x0, x1)), _f(min(y0, y1)), _f(abs(x1 - x0)), _f(abs(y1 - y0)), c, e.get('al', 1)))
        elif t == 'vline':
            x = round(X(e['x'])) + 0.5
            out.append('<path d="M%s %s V%s" class="s-%s" fill="none"%s/>' % (_f(x), _f(T), _f(T + ph), c, dash))
        elif t == 'hline':
            y = round(Y(e['y'], k)) + 0.5
            out.append('<path d="M%s %s H%s" class="s-%s" fill="none" stroke-width="%s"%s/>' % (_f(L), _f(y), _f(L + pw), c, e.get('w', 1), dash))
        elif t == 'band':
            top = [(X(p[0]), Y(p[2], k)) for p in e['pts']]
            bottom = [(X(p[0]), Y(p[1], k)) for p in reversed(e['pts'])]
            out.append('<path d="%s Z" class="f-%s" fill-opacity="%s"/>' % (path(top + bottom), c, e.get('al', 0.18)))
            if e.get('edge'):
                for j in (1, 2):
                    out.append('<path d="%s" class="s-%s" fill="none"%s/>' % (path([(X(p[0]), Y(p[j], k)) for p in e['pts']]), c, dash))
        elif t == 'line':
            pts = [(X(p[0]), Y(p[1], k)) for p in e['pts']]
            out.append('<path d="%s" class="s-%s" fill="none" stroke-width="%s"%s/>' % (path(pts), c, e.get('w', 2), dash))
            if e.get('mk'):
                for x, y in pts:
                    if e.get('open'):
                        out.append('<circle cx="%s" cy="%s" r="%s" class="f-bg s-%s" stroke-width="1.5"/>' % (_f(x), _f(y), e['mk'], c))
                    else:
                        out.append('<circle cx="%s" cy="%s" r="%s" class="f-%s"/>' % (_f(x), _f(y), e['mk'], c))
        elif t == 'pt':
            x, y, r = X(e['x']), Y(e['y'], k), e.get('r', 4)
            if e.get('open'):
                out.append('<circle cx="%s" cy="%s" r="%s" class="s-%s" fill="none" stroke-width="1.8"/>' % (_f(x), _f(y), r, c))
            else:
                out.append('<circle cx="%s" cy="%s" r="%s" class="f-%s"/>' % (_f(x), _f(y), r, c))
        elif t == 'txt':
            if e.get('s'):
                text(e['s'], X(e['x']) + e.get('dx', 0), Y(e['y'], k) + e.get('dy', 0), e.get('al'), e.get('bl'), c, e.get('b', False))
        else:
            raise ValueError('unknown element type %r in %s' % (t, fig.name))

    head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
            'font-family="DejaVu Sans, Helvetica, Arial, sans-serif" font-size="%d">\n' % (W, H, W, H, FONT))
    meta = '<title>%s</title>\n<desc>%s</desc>\n' % (html.escape(title(fig), quote=False), html.escape(fig.aria, quote=False))
    style = '<style>%s@media (prefers-color-scheme: dark){%s}</style>\n' % (_css(LIGHT), _css(DARK))
    return head + meta + style + '\n'.join(out) + '\n</svg>\n'
