"""Line coverage of an experiment's model/ by its own tests, with the standard library only.

    python3 tools/coverage.py <experiment-folder> [--floor PERCENT]

Runs the experiment's tests under the standard library's ``trace`` and reports, for every file in
``model/``, the executable lines the tests ran. A line is executable when a statement starts on it,
docstrings excluded. With ``--floor`` the command exits 1 when the total falls below that percentage.
Tracing slows the tests several times over, so this runs on demand, not in ``check_all.py``.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import trace
import unittest


def executable_lines(source: str) -> set[int]:
    """The lines on which a statement starts, docstrings excluded."""
    lines = set()
    for node in ast.walk(ast.parse(source)):
        body = getattr(node, 'body', None)
        doc = None
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                doc = first
        if isinstance(node, ast.stmt) or isinstance(node, ast.Module):
            for child in (body or []):
                if child is not doc:
                    lines.add(child.lineno)
            for field in ('orelse', 'finalbody', 'handlers'):
                for child in getattr(node, field, None) or []:
                    lines.add(child.lineno)
    return lines


def measure(folder: str) -> dict[str, tuple[int, int]]:
    """For each model file, relative to folder: (executable lines the tests ran, executable lines)."""
    folder = os.path.abspath(folder)
    model, tests = os.path.join(folder, 'model'), os.path.join(folder, 'tests')
    tracer = trace.Trace(count=1, trace=0, ignoredirs=[sys.prefix, sys.exec_prefix])

    def run_tests() -> None:
        # Discovery imports the model, so it runs under the tracer too: import-time lines count.
        suite = unittest.defaultTestLoader.discover(tests, top_level_dir=tests)
        unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)

    tracer.runfunc(run_tests)
    ran: dict[str, set[int]] = {}
    for (path, line), _ in tracer.results().counts.items():
        ran.setdefault(os.path.abspath(path), set()).add(line)
    report = {}
    for name in sorted(os.listdir(model)):
        if not name.endswith('.py'):
            continue
        path = os.path.join(model, name)
        with open(path, encoding='utf-8') as f:
            lines = executable_lines(f.read())
        report['model/' + name] = (len(lines & ran.get(path, set())), len(lines))
    return report


def main(argv: list[str]) -> int:
    if not argv or len(argv) not in (1, 3) or (len(argv) == 3 and argv[1] != '--floor'):
        print('usage: python3 tools/coverage.py <experiment-folder> [--floor PERCENT]', file=sys.stderr)
        return 2
    report = measure(argv[0])
    for name, (run, total) in report.items():
        print('%-36s %5d of %5d lines  %5.1f%%' % (name, run, total, 100.0 * run / total if total else 100.0))
    run = sum(r for r, _ in report.values())
    total = sum(t for _, t in report.values())
    share = 100.0 * run / total if total else 100.0
    print('%-36s %5d of %5d lines  %5.1f%%' % ('total', run, total, share))
    return 1 if len(argv) == 3 and share < float(argv[2]) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
