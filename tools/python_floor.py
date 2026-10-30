"""Report Python files that do not parse under the oldest supported version.

    python3 tools/python_floor.py [folder]

The repository promises Python 3.10 or later. Parsing with ``feature_version=(3, 10)``
rejects most syntax added later, such as ``except*``. Some newer grammar (for example the
f-string changes of 3.12) is not rejected this way, so continuous integration also compiles
every file on Python 3.10 itself.
"""
from __future__ import annotations

import ast
import os
import sys

FLOOR = (3, 10)


def incompatible(folder: str) -> list[tuple[str, str]]:
    """(path, error) for every .py file under folder that does not parse at FLOOR."""
    problems = []
    for base, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d != '__pycache__')
        for name in sorted(files):
            if name.endswith('.py'):
                path = os.path.join(base, name)
                with open(path, encoding='utf-8') as f:
                    source = f.read()
                try:
                    ast.parse(source, filename=path, feature_version=FLOOR)
                except SyntaxError as e:
                    problems.append((path, '%s (line %s)' % (e.msg, e.lineno)))
    return problems


if __name__ == '__main__':
    found = incompatible(sys.argv[1] if len(sys.argv) > 1 else '.')
    for path, error in found:
        print('%s: %s' % (path, error))
    print('%d files fail to parse at Python %d.%d' % ((len(found),) + FLOOR) if found else 'all files parse at Python %d.%d' % FLOOR)
    sys.exit(1 if found else 0)
