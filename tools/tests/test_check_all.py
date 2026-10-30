"""check_all finds every experiment and runs every check, and fails when any check fails."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import check_all  # noqa: E402


def _repo(d):
    os.makedirs(os.path.join(d, 'tools'))
    for slug in ('alpha', 'beta'):
        os.makedirs(os.path.join(d, slug, 'tests'))
        with open(os.path.join(d, slug, 'experiment.json'), 'w', encoding='utf-8') as f:
            json.dump({'slug': slug, 'posts': []}, f)
    os.makedirs(os.path.join(d, 'not-an-experiment'))
    return d


class CheckAllTest(unittest.TestCase):

    def test_finds_only_folders_with_a_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check_all.experiments(_repo(d)), ['alpha', 'beta'])

    def test_fast_checks_cover_every_experiment(self):
        with tempfile.TemporaryDirectory() as d:
            names = [name for name, _ in check_all.steps(_repo(d), full=False)]
        for expected in ('tools tests', 'repository layout', 'python 3.10 floor', 'compile', 'alpha tests', 'alpha docs',
                         'alpha figures', 'beta tests', 'beta docs', 'beta figures'):
            self.assertIn(expected, names)
        self.assertFalse(any(n.endswith('reproduction') for n in names))

    def test_full_adds_the_reproduction(self):
        with tempfile.TemporaryDirectory() as d:
            names = [name for name, _ in check_all.steps(_repo(d), full=True)]
        self.assertIn('alpha reproduction', names)
        self.assertIn('beta reproduction', names)

    def test_run_fails_when_any_step_fails(self):
        ok = ('passes', [sys.executable, '-c', 'pass'])
        bad = ('fails', [sys.executable, '-c', 'raise SystemExit(3)'])
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check_all.run([ok, ok], d, quiet=True), 0)
            self.assertEqual(check_all.run([ok, bad, ok], d, quiet=True), 1)


if __name__ == '__main__':
    unittest.main()
