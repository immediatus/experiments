"""The command line every experiment's reproduce.py shares.

An experiment's reproduce.py defines one function per section, named t1, t2, ..., each
printing a header line that starts with its name (T1, T2, ...) and then its rows. It ends with

    if __name__ == '__main__':
        sys.exit(harness.main(sys.argv[1:], HERE, harness.collect(globals())))

where HERE is the experiment folder. The harness then provides:

    reproduce.py [T1 T2 ...]          print sections, all of them when none is named
    reproduce.py --check              run tests/, then compare every section with expected/results.txt
    reproduce.py --figures            draw figures/<name>.svg from expected/results.txt
    reproduce.py --figures --check    compare the drawings with figures/

Figures come from figures/figspec.py, whose figures(results_path) returns a list of
svg.Figure; an experiment without that file has no figures.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import os
import re
import sys
import unittest
from typing import Callable

import svg

Sections = dict[str, Callable[[], None]]

USAGE = ('usage: reproduce.py [T1 T2 ...]   print sections (all when none are named)\n'
         '       reproduce.py --check        run the tests, then every section against expected/results.txt\n'
         '       reproduce.py --figures [--check]   draw the SVG figures, or compare them with figures/')


def collect(namespace: dict) -> Sections:
    """The section functions of a module's namespace, t1, t2, ..., by name T1, T2, ... in
    numeric order."""
    found = [(int(m.group(1)), fn) for name, fn in namespace.items()
             if callable(fn) and (m := re.fullmatch(r't(\d+)', name))]
    return {'T%d' % n: fn for n, fn in sorted(found)}


def run_tests(here: str) -> None:
    """Run the experiment's tests/; exit if any fails, since numbers from a model that fails its
    own tests prove nothing."""
    tests = os.path.join(here, 'tests')
    suite = unittest.defaultTestLoader.discover(tests, top_level_dir=tests)
    report = io.StringIO()
    result = unittest.TextTestRunner(stream=report, verbosity=1).run(suite)
    if not result.wasSuccessful():
        sys.stderr.write(report.getvalue())
        sys.exit('tests failed: the model is wrong, so no number is checked')
    print('tests: %d pass' % result.testsRun)


def output(sections: Sections) -> str:
    """Everything the sections print, in order."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        for section in sections.values():
            section()
    return buf.getvalue()


def check(here: str, sections: Sections) -> None:
    """Run the tests, then every section, and compare the output with expected/results.txt byte
    for byte; exit at the first line that differs."""
    run_tests(here)
    got = output(sections)
    with open(os.path.join(here, 'expected', 'results.txt'), encoding='utf-8') as f:
        want = f.read()
    if got == want:
        print('identical')
        return
    g, w = got.splitlines(), want.splitlines()
    for i, (x, y) in enumerate(zip(g, w), 1):
        if x != y:
            sys.exit('differs at line %d\n  got:      %s\n  expected: %s' % (i, x, y))
    sys.exit('differs in length: got %d lines, expected %d' % (len(g), len(w)))


def figure_specs(here: str) -> list[svg.Figure]:
    """The experiment's figures, built by figures/figspec.py from expected/results.txt; none if
    the experiment has no figspec."""
    folder = os.path.join(here, 'figures')
    if not os.path.isfile(os.path.join(folder, 'figspec.py')):
        return []
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return importlib.import_module('figspec').figures(os.path.join(here, 'expected', 'results.txt'))


def figures(here: str, compare: bool = False) -> None:
    """Draw every figure as figures/<name>.svg, or compare the drawings with what is there."""
    out = os.path.join(here, 'figures')
    figs = figure_specs(here)
    differ = []
    for fig in figs:
        doc = svg.render(fig)
        path = os.path.join(out, fig.name + '.svg')
        if compare:
            try:
                with open(path, encoding='utf-8') as f:
                    same = f.read() == doc
            except FileNotFoundError:
                same = False
            if not same:
                differ.append(fig.name)
        else:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(doc)
    if compare:
        if differ:
            sys.exit('figures differ: ' + ', '.join(differ))
        print('figures identical' if figs else 'no figures')
    else:
        print('wrote %d figures to %s' % (len(figs), out))


def main(argv: list[str], here: str, sections: Sections) -> int:
    """Dispatch reproduce.py's command line; the exit status."""
    if argv in (['--figures'], ['--figures', '--check']):
        figures(here, compare=len(argv) == 2)
        return 0
    if argv == ['--check']:
        check(here, sections)
        return 0
    if any(a.startswith('-') for a in argv):
        sys.stderr.write(USAGE + '\n')
        return 2
    unknown = [a for a in argv if a not in sections]
    if unknown:
        sys.stderr.write('unknown section %s; choose from: %s\n%s\n' % (' '.join(unknown), ' '.join(sections), USAGE))
        return 2
    for name in argv or sections:
        sections[name]()
    return 0
