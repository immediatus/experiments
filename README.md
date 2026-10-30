# Experiments

The simulations, data and figures behind the blog series on
**[e-mindset.space](https://e-mindset.space)**. Each series that rests on executed code has
a folder here. It holds the code that produced every number the posts quote and the output it
produced. The figures are drawn from that output, and the documents connect each claim to its
evidence. Anyone can rerun it and get the same numbers, byte for byte.

## Series

| Series | Folder | What it reproduces |
|---|---|---|
| [Capacity in Arrears: Autoscaling Under Dead Time, Saturated Metrics, and Retry Debt](https://e-mindset.space/blog/capacity-in-arrears-part1-one-bit-per-dead-time/) (2026) | [`capacity-in-arrears/`](capacity-in-arrears/) | A port of the Kubernetes autoscaler's replica calculation checked against its upstream tests, the fluid and request-level simulations of four posts, 49 result sections, 24 figures, and a kit for testing the predictions on a real cluster |

## Check any experiment

Python 3.10 or later, standard library only. Nothing to install.

```bash
git clone https://github.com/immediatus/experiments.git && cd experiments
python3 capacity-in-arrears/reproduce.py --check            # prints "identical" (about six minutes)
python3 capacity-in-arrears/reproduce.py --figures --check  # prints "figures identical"
```

Each experiment's README explains what it is, links to its posts and says what is where.

## Repository

| Path | Purpose |
|---|---|
| `<series>/` | One experiment per series, named by the series' URL slug |
| [`tools/`](tools/) | Shared utilities: the command line every experiment shares, the results reader, the SVG figure renderer, the repository and documentation checks, the Python-version check |
| [`CONVENTIONS.md`](CONVENTIONS.md) | The standard every experiment follows: layout, code, figures, documents, checks, releases |
| [`CHANGELOG.md`](CHANGELOG.md) | Releases and dated errata |
| [`CITATION.cff`](CITATION.cff) | How to cite this repository |
| `pyproject.toml`, `requirements-dev.txt`, `.python-version` | Lint configuration, pinned development tools, the interpreter for pyenv |

Continuous integration runs the fast checks of every experiment (tests, documents, figures,
the Python 3.10 floor, lint) on every push to main and every pull request, on Python 3.10 to
3.14. The full byte-for-byte reproduction runs weekly, on every release tag and on demand, on
Python 3.10 and 3.14.

## Development

Running an experiment needs only Python 3.10 or later. To work on the repository:

```bash
pyenv install --skip-existing "$(cat .python-version)"   # optional: the interpreter CI uses for lint
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt                        # development tools only (ruff, pinned)
python3 tools/check_all.py                                 # every fast check, as CI runs it
python3 tools/check_all.py --full                          # plus each byte-for-byte reproduction
ruff check .
```

`pyproject.toml` holds tool configuration only; nothing in this repository is installed as a
package.

## Reporting

Found a number, figure or claim that does not match? Ran a falsification criterion on real
infrastructure? Open an issue with the matching template. A refutation is a result, and it is
recorded as one.

## Licence

[Apache-2.0](LICENSE). Experiments that derive from third-party code credit it in their
`NOTICE` file.
