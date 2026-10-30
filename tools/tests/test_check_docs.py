"""check_docs catches each kind of inconsistency between an experiment's documents and its results."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import check_docs  # noqa: E402

POST = 'https://e-mindset.space/blog/series-part1-first/'


def _experiment(d, statement='peaks at 317 pods', extra='', section='T2'):
    for sub in ('expected', 'figures', 'docs'):
        os.makedirs(os.path.join(d, sub))
    with open(os.path.join(d, 'experiment.json'), 'w', encoding='utf-8') as f:
        json.dump({'title': 'Series', 'slug': 'series', 'blog': 'https://e-mindset.space',
                   'posts': [{'part': 1, 'title': 'First', 'url': POST}]}, f)
    with open(os.path.join(d, 'expected', 'results.txt'), 'w', encoding='utf-8') as f:
        f.write('T2 staircase\n    10x | 3 |   345 s | 3.17 | 1836\n  peak 317\n'
                'T5 orders\n  10x | (0,10,10) (510,317,159)\n')
    with open(os.path.join(d, 'figures', 'staircase.svg'), 'w', encoding='utf-8') as f:
        f.write('<svg/>')
    with open(os.path.join(d, 'docs', 'CLAIMS.md'), 'w', encoding='utf-8') as f:
        f.write('| Claim | Layer | Statement | Section | Figure | Post | Derived from |\n|---|---|---|---|---|---|---|\n')
        f.write('| Staircase | Estimate | %s | %s | [fig](../figures/staircase.svg) | [post](%s#prop-2) | |\n' % (statement, section, POST))
    with open(os.path.join(d, 'docs', 'part1.md'), 'w', encoding='utf-8') as f:
        f.write('See [claims](CLAIMS.md) and section T2.\n' + extra)
    return d


def _errors(**kw):
    with tempfile.TemporaryDirectory() as d:
        return check_docs.check(_experiment(d, **kw))


class CheckDocsTest(unittest.TestCase):

    def test_clean_experiment_passes(self):
        self.assertEqual(_errors(), [])

    def test_number_not_in_results_fails(self):
        self.assertTrue(any('318' in e for e in _errors(statement='peaks at 318 pods')))

    def test_rounded_number_passes(self):
        self.assertEqual(_errors(statement='overshoot 3.2 times'), [])

    def test_formula_numbers_are_not_results(self):
        self.assertEqual(_errors(statement='needs $\\lceil \\log_2 (k/2) \\rceil$ rounds'), [])

    def test_missing_figure_fails(self):
        self.assertTrue(any('hunt.svg' in e for e in _errors(extra='![x](../figures/hunt.svg)\n')))

    def test_unknown_section_fails(self):
        self.assertTrue(any('T99' in e for e in _errors(extra='Run section T99.\n')))

    def test_unknown_section_in_parentheses_fails(self):
        self.assertTrue(any('T99' in e for e in _errors(extra='The boundary (T99) holds.\n')))

    def test_post_not_in_manifest_fails(self):
        self.assertTrue(any('no-such-post' in e for e in _errors(extra='[x](https://e-mindset.space/blog/no-such-post/)\n')))

    def test_blog_home_page_passes(self):
        self.assertEqual(_errors(extra='[home](https://e-mindset.space) and [home](https://e-mindset.space/)\n'), [])

    def test_links_outside_the_blog_are_not_posts(self):
        self.assertEqual(_errors(extra='[k8s](https://kubernetes.io/docs/)\n'), [])

    def test_broken_relative_link_fails(self):
        self.assertTrue(any('MISSING.md' in e for e in _errors(extra='[x](../MISSING.md)\n')))

    def test_values_inside_a_tuple_are_separate_numbers(self):
        self.assertEqual(_errors(statement='orders 159 then 317', section='T5'), [])

    def test_number_must_be_in_a_cited_section(self):
        self.assertTrue(any('345' in e for e in _errors(statement='capacity at 345 s', section='T5')))


if __name__ == '__main__':
    unittest.main()
