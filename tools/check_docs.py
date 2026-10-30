"""Check that an experiment's documents agree with what its code produced.

    python3 tools/check_docs.py <experiment-folder>

Prints ``docs consistent`` or one line per problem, and exits 1 on any problem.

Every Markdown file in the experiment is read, and four things are checked:

* a relative link or image points at a file that exists;
* a link into the blog named by ``experiment.json`` (``blog``), other than the blog's home page,
  points at one of the posts the manifest lists;
* a section name such as ``T12`` is a section of ``expected/results.txt``;
* every number in the *Statement* column of ``docs/CLAIMS.md`` is a value printed by one of
  the sections the row cites, possibly rounded to the decimals the statement shows.

Whole numbers up to 12 are exempt from the last check, because they count things (rounds,
retries, parts) rather than report results. Text between ``$`` signs is notation and is
skipped. A number obtained by arithmetic belongs in the *Derived from* column, which is
not checked.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Iterator

import results

LINK = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)\)')
SECTION = re.compile(r'\bT(\d+)\b')
NUMBER = re.compile(r'(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\w])')
FORMULA = re.compile(r'\$[^$]*\$')


def markdown_files(folder: str) -> Iterator[str]:
    """Every Markdown file under folder, skipping hidden and cache directories."""
    for base, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d != '__pycache__')
        for name in sorted(files):
            if name.endswith('.md'):
                yield os.path.join(base, name)


def manifest(folder: str) -> dict:
    """The experiment's experiment.json."""
    with open(os.path.join(folder, 'experiment.json'), encoding='utf-8') as f:
        return json.load(f)


def _numbers(text: str) -> list[float]:
    """Numbers in a block of results. Inside parentheses a comma separates values, as in the
    tuples (510,317,159); elsewhere it groups thousands, as in 1,836."""
    text = re.sub(r'\(([^()]*)\)', lambda m: '(' + m.group(1).replace(',', ' ') + ')', text)
    values = []
    for t in re.findall(r'\d[\d,]*\.?\d*', text):
        t = t.replace(',', '').rstrip('.')
        if t.replace('.', '', 1).isdigit():
            values.append(float(t))
    return values


def section_values(folder: str) -> dict[str, list[float]]:
    """The numbers printed by each section of expected/results.txt, header included, by name."""
    blocks = results.read(os.path.join(folder, 'expected', 'results.txt'))
    return {name: _numbers(block) for name, block in blocks.items()}


def is_result(token: str, decimals: str, values: list[float]) -> bool:
    """Whether a number written with the given decimals matches a printed result."""
    value = float(token.replace(',', '') + ('.' + decimals if decimals else ''))
    if not decimals and value <= 12:
        return True
    places = len(decimals)
    return any(round(v, places) == value for v in values)


def claim_numbers(path: str, values: dict[str, list[float]]) -> list[str]:
    """Problems with the numbers in the Statement column of a claims table. Each number must be
    printed by one of the sections the row cites; a row that cites none is checked against all."""
    with open(path, encoding='utf-8') as f:
        rows = [line for line in f.read().splitlines() if line.startswith('|')]
    errors = []
    header = None
    everything = [v for vs in values.values() for v in vs]
    for row in rows:
        cells = [c.strip() for c in row.strip('|').split('|')]
        if 'Statement' in cells:
            header = cells
            continue
        if header is None or set(row) <= set('|-: '):
            continue
        cited = ['T' + n for n in SECTION.findall(cells[header.index('Section')])] if 'Section' in header else []
        pool = [v for name in cited for v in values.get(name, [])] if cited else everything
        statement = FORMULA.sub('', cells[header.index('Statement')])
        for token, decimals in NUMBER.findall(statement):
            if not is_result(token, decimals, pool):
                shown = token + ('.' + decimals if decimals else '')
                where = 'sections ' + ', '.join(cited) if cited else 'expected/results.txt'
                errors.append('%s: %s in "%s" is not printed by %s' % (os.path.basename(path), shown, statement, where))
    return errors


def check(folder: str) -> list[str]:
    """Every problem found in the experiment's documents; an empty list means consistent."""
    errors = []
    meta = manifest(folder)
    home = meta['blog'].rstrip('/')
    posts = {p['url'] for p in meta['posts']}
    values = section_values(folder)
    for path in markdown_files(folder):
        rel = os.path.relpath(path, folder)
        with open(path, encoding='utf-8') as f:
            text = f.read()
        for target in LINK.findall(text):
            if target.startswith(('http://', 'https://')):
                page = target.split('#')[0]
                if page.startswith(home) and page.rstrip('/') != home and page not in posts:
                    errors.append('%s: %s is not a post of this series' % (rel, target))
            elif not target.startswith(('mailto:', '#')):
                local = os.path.normpath(os.path.join(os.path.dirname(path), target.split('#')[0]))
                if not os.path.exists(local):
                    errors.append('%s: link to missing file %s' % (rel, target))
        for n in SECTION.findall(LINK.sub('', text)):
            if 'T' + n not in values:
                errors.append('%s: section T%s is not in expected/results.txt' % (rel, n))
    claims = os.path.join(folder, 'docs', 'CLAIMS.md')
    if os.path.exists(claims):
        errors += claim_numbers(claims, values)
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[0])
        print('usage: python3 tools/check_docs.py <experiment-folder>')
        return 2
    problems = check(os.path.abspath(argv[0]))
    for p in problems:
        print(p)
    if not problems:
        print('docs consistent')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
