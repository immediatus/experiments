"""Read an experiment's results file, ``expected/results.txt``.

The file is the concatenated output of the experiment's sections. Each section opens with a
header line that starts with its name, ``T`` and a number, then a space; the lines after it, up
to the next header, are its rows:

    T2 saturated CPU: overload | rounds | time to capacity
         3x | 1 |   105 s
        10x | 3 |   345 s

    read(path) -> {name: block}     blocks in file order, each with its header line
    rows(block) -> [row, ...]       the rows after the header, stripped, blank lines dropped
    cells(row) -> [cell, ...]       the row split on '|', each cell stripped
    number(text) -> float           the number in a cell, ignoring units and thousands commas
"""
from __future__ import annotations

import re

HEADER = re.compile(r'^(T\d+) ', re.M)


def parse(text: str) -> dict[str, str]:
    """Each section's block of text, header line included, by name, in file order."""
    starts = [(m.start(), m.group(1)) for m in HEADER.finditer(text)]
    ends = [s for s, _ in starts[1:]] + [len(text)]
    return {name: text[start:end] for (start, name), end in zip(starts, ends)}


def read(path: str) -> dict[str, str]:
    """parse() of the file at path."""
    with open(path, encoding='utf-8') as f:
        return parse(f.read())


def rows(block: str) -> list[str]:
    """The rows of a section block: every non-blank line after the header, stripped."""
    return [line.strip() for line in block.splitlines()[1:] if line.strip()]


def cells(row: str) -> list[str]:
    """A row split on '|', each cell stripped."""
    return [c.strip() for c in row.split('|')]


def number(text: str) -> float:
    """The number in a cell such as '345 s', '3.17x' or '1,836': everything but digits, the
    decimal point, an exponent and a sign is dropped."""
    return float(re.sub(r'[^0-9.eE+-]', '', text))
