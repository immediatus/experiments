# Tools

Utilities shared by every experiment. Standard library only, Python 3.10 or later, each with
its own tests in [`tests/`](tests/):

```bash
python3 -m unittest discover -s tools/tests
```

| Tool | What it does | Used as |
|---|---|---|
| [`harness.py`](harness.py) | The command line every experiment's `reproduce.py` shares: finds the sections `t1`, `t2`, ..., prints them, runs `tests/` and compares every section with `expected/results.txt` (`--check`), draws or compares the figures (`--figures`) | the last line of each `reproduce.py` |
| [`results.py`](results.py) | Reads a results file into sections, rows, cells and numbers; the one parser figures and checks share | `figspec.py`, `check_docs.py`, `check_repo.py` |
| [`check_repo.py`](check_repo.py) | Checks that every experiment follows CONVENTIONS.md: required files, manifest schema, posts linked, SECTIONS.md matching the results, a "Reporting a run" section, every figure referenced by a document, the harness used; and that the repository's README and CHANGELOG list it | `python3 tools/check_repo.py` |
| [`svg.py`](svg.py) | Draws a figure specification as a standalone SVG: the same layout as the blog's canvas figures, light and dark palettes, a description for screen readers, byte-stable output | `reproduce.py --figures` in each experiment |
| [`check_docs.py`](check_docs.py) | Checks an experiment's documents against its code and results: links, post URLs from `experiment.json`, section names, every number in `docs/CLAIMS.md`, every labelled result the claims name present on a companion page, and the falsification criteria numbered without a gap | `python3 tools/check_docs.py <experiment>` |
| [`check_all.py`](check_all.py) | Runs every check of every experiment, the same way locally and in CI; `--full` adds the byte-for-byte reproductions, under two hash seeds | `python3 tools/check_all.py [--full]` |
| [`lint.py`](lint.py) | Ruff with the pinned rules when installed; otherwise a standard-library check for unused imports, imports of another module's private names, imports inside a function and `open()` without an encoding | `python3 tools/lint.py` |
| [`coverage.py`](coverage.py) | Line coverage of an experiment's `model/` by its own tests, measured with the standard library's `trace` | `python3 tools/coverage.py <experiment>` |
| [`python_floor.py`](python_floor.py) | Reports Python files that use syntax newer than 3.10, such as `except*`; continuous integration also compiles every file on Python 3.10 itself, which catches the rest | `python3 tools/python_floor.py .` |

A change to a tool runs every experiment's checks in continuous integration, so it cannot
silently move a published figure or number.
