"""Lint the repository: ruff with the rules of pyproject.toml when it is installed, otherwise a fallback.

    python3 tools/lint.py [path ...]     # the repository root when no path is given

The fallback needs only the standard library and checks the rules most likely to rot in research code: an
imported name that is never used (ruff's F401), a name imported from another module that the module keeps
private by a leading underscore, and a text-mode open() without an explicit encoding (PLW1514). A line marked
``# noqa: F401`` re-exports on purpose and is skipped.
Prints one line per problem and exits 1 on any.
"""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys

SKIP = {'.git', '__pycache__', '.venv', 'venv', '.ruff_cache', 'PGenerated', 'PCheckerOutput'}


def python_files(paths: list[str]) -> list[str]:
    """Every .py file under the paths, skipping caches and generated output."""
    out = []
    for p in paths:
        if os.path.isfile(p):
            out.append(p)
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = sorted(d for d in dirs if d not in SKIP)
            out += [os.path.join(root, f) for f in sorted(files) if f.endswith('.py')]
    return out


def _used_names(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            base = node
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                names.add(base.id)
    annotations = [n.annotation for n in ast.walk(tree) if isinstance(n, (ast.arg, ast.AnnAssign)) and n.annotation]
    annotations += [n.returns for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.returns]
    for ann in annotations:
        for node in ast.walk(ann):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value.replace('[', ' ').replace(']', ' ').replace(',', ' ').replace('|', ' ')
                names.update(part.split('.')[0] for part in text.split())
    return names


def fallback(files: list[str]) -> list[str]:
    """Unused imports and private imports in the files, one message each."""
    problems = []
    for path in files:
        with open(path, encoding='utf-8') as f:
            source = f.read()
        lines = source.splitlines()
        tree = ast.parse(source, filename=path)
        used = _used_names(tree)
        exported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__all__' for t in node.targets):
                exported |= {e.value for e in getattr(node.value, 'elts', []) if isinstance(e, ast.Constant)}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if 'noqa: F401' in lines[node.lineno - 1]:
                continue
            for alias in node.names:
                name = (alias.asname or alias.name).split('.')[0]
                if name == '*' or (isinstance(node, ast.ImportFrom) and node.module == '__future__'):
                    continue
                if name not in used and name not in exported:
                    problems.append('%s:%d: unused import %s' % (path, node.lineno, name))
                if isinstance(node, ast.ImportFrom) and alias.name.startswith('_') and not alias.name.startswith('__'):
                    problems.append('%s:%d: imports private name %s from %s' % (path, node.lineno, alias.name, node.module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'open':
                mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == 'mode'), None)
                binary = isinstance(mode, ast.Constant) and 'b' in str(mode.value)
                if not binary and not any(k.arg == 'encoding' for k in node.keywords):
                    problems.append('%s:%d: open() without an encoding' % (path, node.lineno))
    return problems


def main(argv: list[str]) -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = argv or [root]
    ruff = shutil.which('ruff')
    if ruff:
        return subprocess.run([ruff, 'check', *paths], cwd=root).returncode
    problems = fallback(python_files(paths))
    for p in problems:
        print(p)
    print('lint clean (fallback; install ruff for the full rules)' if not problems else '%d problems' % len(problems))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
