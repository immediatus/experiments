"""Run every check of the repository, the same way locally and in continuous integration.

    python3 tools/check_all.py          # fast checks: layout, tests, documents, figures, Python floor
    python3 tools/check_all.py --full   # also every experiment's byte-for-byte reproduction

An experiment is a top-level folder with an ``experiment.json``. Each step runs as its own
process from the repository root; the run reports every step and exits 1 if any failed.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

Step = tuple[str, list[str]]  # (name, argv)


def experiments(root: str) -> list[str]:
    """Top-level folders that carry an experiment.json, in name order."""
    return sorted(d for d in os.listdir(root)
                  if os.path.isfile(os.path.join(root, d, 'experiment.json')))


def steps(root: str, full: bool) -> list[Step]:
    """Every check, in the order it runs."""
    py = sys.executable
    out = [
        ('tools tests', [py, '-m', 'unittest', 'discover', '-s', 'tools/tests']),
        ('repository layout', [py, 'tools/check_repo.py', '.']),
        ('python 3.10 floor', [py, 'tools/python_floor.py', '.']),
        ('compile', [py, '-m', 'compileall', '-q', '-x', r'/\.git/', '.']),
    ]
    for slug in experiments(root):
        out.append((slug + ' tests', [py, '-m', 'unittest', 'discover', '-s', slug + '/tests']))
        out.append((slug + ' docs', [py, 'tools/check_docs.py', slug]))
        out.append((slug + ' figures', [py, slug + '/reproduce.py', '--figures', '--check']))
        if full:
            out.append((slug + ' reproduction', [py, slug + '/reproduce.py', '--check']))
    return out


def run(plan: list[Step], root: str, quiet: bool = False) -> int:
    """Run each step from root; 0 if every step passed, 1 otherwise."""
    failed = []
    for name, argv in plan:
        start = time.monotonic()
        r = subprocess.run(argv, cwd=root, capture_output=True, text=True)
        seconds = time.monotonic() - start
        if r.returncode:
            failed.append(name)
        if not quiet:
            print('%-4s %-40s %7.1f s' % ('ok' if r.returncode == 0 else 'FAIL', name, seconds), flush=True)
            if r.returncode:
                sys.stdout.write((r.stdout + r.stderr)[-4000:] + '\n')
    if not quiet:
        print('%d of %d checks passed' % (len(plan) - len(failed), len(plan)) + ('' if not failed else '; failed: ' + ', '.join(failed)))
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    if argv not in ([], ['--full']):
        print('usage: python3 tools/check_all.py [--full]', file=sys.stderr)
        return 2
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return run(steps(root, full=argv == ['--full']), root)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
