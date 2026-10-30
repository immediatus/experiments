"""Check that every experiment follows the repository's standard (CONVENTIONS.md, sections 1, 2
and 5) and that the repository indexes it.

    python3 tools/check_repo.py [repository-root]

Prints ``repository consistent`` or one line per problem, and exits 1 on any problem.

For each experiment, a top-level folder with an ``experiment.json``:

* the required files and folders exist, and the top level holds no other files;
* the manifest has the required fields, its slug is the folder's name, and every post lies
  under its blog;
* the README links every post the manifest lists;
* docs/SECTIONS.md lists exactly the sections of expected/results.txt;
* docs/FALSIFICATION.md has a "Reporting a run" section;
* every figure in figures/ is shown by at least one of the experiment's documents, since a
  generated file that nothing references does not belong in the repository;
* reproduce.py hands its command line to the shared harness.

For the repository: the README links every experiment's folder, and CHANGELOG.md has a
heading for each.
"""
from __future__ import annotations

import json
import os
import re
import sys

import results

REQUIRED_FILES = ['README.md', 'experiment.json', 'reproduce.py', 'expected/results.txt',
                  'docs/CLAIMS.md', 'docs/SECTIONS.md', 'docs/FALSIFICATION.md',
                  'docs/ASSUMPTIONS.md', 'docs/SOURCES.md']
REQUIRED_FOLDERS = ['model', 'tests']
TOP_LEVEL_FILES = {'README.md', 'experiment.json', 'reproduce.py', 'NOTICE'}
MANIFEST = {'title': str, 'slug': str, 'blog': str, 'posts': list, 'python': str, 'dependencies': list}
POST = {'part': int, 'title': str, 'url': str}
SECTION_ROW = re.compile(r'^\|\s*(T\d+)\s*\|', re.M)


def experiments(root: str) -> list[str]:
    """Top-level folders that carry an experiment.json, in name order."""
    return sorted(d for d in os.listdir(root) if os.path.isfile(os.path.join(root, d, 'experiment.json')))


def _read(path: str) -> str:
    with open(path, encoding='utf-8') as f:
        return f.read()


def manifest_problems(meta: dict, slug: str) -> list[str]:
    """Problems with one experiment's manifest."""
    errors = ['field %r missing or not a %s' % (k, t.__name__) for k, t in MANIFEST.items() if not isinstance(meta.get(k), t)]
    if errors:
        return errors
    if meta['slug'] != slug:
        errors.append('slug %r is not the folder name %r' % (meta['slug'], slug))
    if not meta['blog'].startswith('https://'):
        errors.append('blog %r is not an https URL' % meta['blog'])
    if not meta['posts']:
        errors.append('no posts listed')
    for i, post in enumerate(meta['posts'], 1):
        bad = [k for k, t in POST.items() if not isinstance(post.get(k), t)]
        if bad:
            errors.append('post %d: field %s missing or of the wrong type' % (i, ', '.join(bad)))
            continue
        if post['part'] != i:
            errors.append('post %d: part is %d; parts are numbered 1, 2, ... in order' % (i, post['part']))
        if not post['url'].startswith(meta['blog'].rstrip('/') + '/'):
            errors.append('post %d: %s is not under the blog %s' % (i, post['url'], meta['blog']))
    if meta['dependencies']:
        errors.append('dependencies %s: experiments use the standard library only' % meta['dependencies'])
    return errors


def experiment_problems(root: str, slug: str) -> list[str]:
    """Problems with one experiment's layout, manifest and documents, each prefixed with its slug."""
    here = os.path.join(root, slug)
    errors = ['missing %s' % p for p in REQUIRED_FILES if not os.path.isfile(os.path.join(here, p))]
    errors += ['missing folder %s/' % p for p in REQUIRED_FOLDERS if not os.path.isdir(os.path.join(here, p))]
    errors += ['%s belongs in a folder: the top level holds only %s' % (name, ', '.join(sorted(TOP_LEVEL_FILES)))
               for name in sorted(os.listdir(here))
               if os.path.isfile(os.path.join(here, name)) and name not in TOP_LEVEL_FILES]
    try:
        meta = json.loads(_read(os.path.join(here, 'experiment.json')))
    except (OSError, ValueError) as e:
        return ['%s: experiment.json unreadable: %s' % (slug, e)]
    manifest = manifest_problems(meta, slug)
    errors += ['experiment.json: ' + e for e in manifest]
    readme = os.path.join(here, 'README.md')
    if not manifest and os.path.isfile(readme):
        text = _read(readme)
        errors += ['README.md does not link the post %s' % p['url'] for p in meta['posts'] if p['url'] not in text]
    res, table = os.path.join(here, 'expected', 'results.txt'), os.path.join(here, 'docs', 'SECTIONS.md')
    if os.path.isfile(res) and os.path.isfile(table):
        printed, listed = list(results.read(res)), SECTION_ROW.findall(_read(table))
        errors += ['docs/SECTIONS.md does not list %s' % n for n in printed if n not in listed]
        errors += ['docs/SECTIONS.md lists %s, which expected/results.txt does not print' % n for n in listed if n not in printed]
    falsification = os.path.join(here, 'docs', 'FALSIFICATION.md')
    if os.path.isfile(falsification) and not re.search(r'^## Reporting a run$', _read(falsification), re.M):
        errors.append('docs/FALSIFICATION.md has no "## Reporting a run" section')
    figures = os.path.join(here, 'figures')
    if os.path.isdir(figures):
        docs = ''.join(_read(os.path.join(base, n)) for base, _, names in os.walk(here) for n in names if n.endswith('.md'))
        errors += ['figures/%s is not referenced by any document' % n for n in sorted(os.listdir(figures))
                   if n.endswith('.svg') and 'figures/' + n not in docs]
    entry = os.path.join(here, 'reproduce.py')
    if os.path.isfile(entry) and 'harness.main(' not in _read(entry):
        errors.append('reproduce.py does not hand its command line to tools/harness.py')
    return ['%s: %s' % (slug, e) for e in errors]


def check(root: str) -> list[str]:
    """Every problem in the repository; an empty list means consistent."""
    errors = []
    slugs = experiments(root)
    readme, changelog = _read(os.path.join(root, 'README.md')), _read(os.path.join(root, 'CHANGELOG.md'))
    for slug in slugs:
        errors += experiment_problems(root, slug)
        if '(%s/)' % slug not in readme:
            errors.append('README.md does not link the experiment folder %s/' % slug)
        if not re.search(r'^### %s$' % re.escape(slug), changelog, re.M):
            errors.append('CHANGELOG.md has no "### %s" heading' % slug)
    return errors


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print('usage: python3 tools/check_repo.py [repository-root]')
        return 2
    problems = check(os.path.abspath(argv[0] if argv else '.'))
    for p in problems:
        print(p)
    if not problems:
        print('repository consistent')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
