"""check_repo catches each departure from the repository's standard."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import check_repo  # noqa: E402

BLOG = 'https://e-mindset.space'
POST = BLOG + '/blog/series-part1-first/'


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _repo(d, **meta):
    """A repository with one compliant experiment, 'series'; meta overrides manifest fields."""
    e = os.path.join(d, 'series')
    manifest = {'title': 'Series', 'slug': 'series', 'blog': BLOG, 'python': '>=3.10', 'dependencies': [],
                'posts': [{'part': 1, 'title': 'First', 'url': POST}]}
    manifest.update(meta)
    _write(os.path.join(e, 'experiment.json'), json.dumps(manifest))
    _write(os.path.join(e, 'README.md'), '[First](%s)\n' % POST)
    _write(os.path.join(e, 'reproduce.py'), 'sys.exit(harness.main(sys.argv[1:], HERE, harness.collect(globals())))\n')
    _write(os.path.join(e, 'expected', 'results.txt'), 'T1 first\n  1 | 2\nT2 second\n  3\n')
    _write(os.path.join(e, 'docs', 'SECTIONS.md'), '| Section | Prints |\n|---|---|\n| T1 | first |\n| T2 | second |\n')
    _write(os.path.join(e, 'docs', 'FALSIFICATION.md'), '# Falsification\n\n## Reporting a run\n\nAttach the data.\n')
    for doc in ('CLAIMS', 'ASSUMPTIONS', 'SOURCES'):
        _write(os.path.join(e, 'docs', doc + '.md'), '# %s\n' % doc)
    for folder in ('model', 'tests'):
        os.makedirs(os.path.join(e, folder))
    _write(os.path.join(d, 'README.md'), '| [Series](%s) | [`series/`](series/) |\n' % POST)
    _write(os.path.join(d, 'CHANGELOG.md'), '# Changelog\n\n### series\n\n- First release.\n')
    return d


def _problems(change=None, **meta):
    with tempfile.TemporaryDirectory() as d:
        _repo(d, **meta)
        if change:
            change(d)
        return check_repo.check(d)


def _edit(rel, old, new):
    def change(d):
        path = os.path.join(d, rel)
        with open(path, encoding='utf-8') as f:
            text = f.read()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text.replace(old, new))
    return change


class CheckRepoTest(unittest.TestCase):

    def test_compliant_repository_passes(self):
        self.assertEqual(_problems(), [])

    def test_missing_required_file_fails(self):
        self.assertTrue(any('ASSUMPTIONS' in p for p in _problems(lambda d: os.remove(os.path.join(d, 'series', 'docs', 'ASSUMPTIONS.md')))))

    def test_loose_top_level_file_fails(self):
        self.assertTrue(any('notes.txt' in p for p in _problems(lambda d: _write(os.path.join(d, 'series', 'notes.txt'), 'x'))))

    def test_slug_must_be_the_folder_name(self):
        self.assertTrue(any('folder name' in p for p in _problems(slug='other')))

    def test_post_outside_the_blog_fails(self):
        posts = [{'part': 1, 'title': 'First', 'url': 'https://elsewhere.example/post/'}]
        self.assertTrue(any('not under the blog' in p for p in _problems(posts=posts)))

    def test_parts_are_numbered_in_order(self):
        posts = [{'part': 2, 'title': 'First', 'url': POST}]
        self.assertTrue(any('numbered' in p for p in _problems(posts=posts)))

    def test_dependencies_are_not_allowed(self):
        self.assertTrue(any('standard library' in p for p in _problems(dependencies=['numpy'])))

    def test_readme_must_link_every_post(self):
        self.assertTrue(any('does not link the post' in p for p in _problems(_edit('series/README.md', POST, BLOG))))

    def test_sections_table_must_match_the_results(self):
        found = _problems(_edit('series/docs/SECTIONS.md', '| T2 | second |\n', '| T3 | third |\n'))
        self.assertTrue(any('does not list T2' in p for p in found))
        self.assertTrue(any('lists T3' in p for p in found))

    def test_falsification_needs_a_reporting_section(self):
        self.assertTrue(any('Reporting a run' in p for p in _problems(_edit('series/docs/FALSIFICATION.md', '## Reporting a run', '## Other'))))

    def test_reproduce_must_use_the_harness(self):
        self.assertTrue(any('harness' in p for p in _problems(_edit('series/reproduce.py', 'harness.main(', 'run('))))

    def test_unreferenced_figure_fails(self):
        def change(d):
            _write(os.path.join(d, 'series', 'figures', 'shown.svg'), '<svg/>')
            _write(os.path.join(d, 'series', 'figures', 'orphan.svg'), '<svg/>')
            _write(os.path.join(d, 'series', 'docs', 'part1.md'), '![shown](../figures/shown.svg)\n')
        found = _problems(change)
        self.assertTrue(any('orphan.svg' in p for p in found))
        self.assertFalse(any('shown.svg' in p for p in found))

    def test_repository_readme_must_link_the_folder(self):
        self.assertTrue(any('experiment folder' in p for p in _problems(_edit('README.md', '(series/)', '(x/)'))))

    def test_changelog_needs_a_heading(self):
        self.assertTrue(any('CHANGELOG' in p for p in _problems(_edit('CHANGELOG.md', '### series', '### other'))))


if __name__ == '__main__':
    unittest.main()
