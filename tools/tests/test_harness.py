"""harness collects an experiment's sections, checks them against the frozen results, draws its
figures and dispatches its command line."""
import contextlib
import io
import itertools
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import harness  # noqa: E402

# unittest imports each test module by name once per process, so every scratch experiment
# gets a test module of its own name.
COUNT = itertools.count()
TEST = 'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(%s)\n'


def t2():
    print('T2 second\n  2')


def t10():
    print('T10 tenth\n  10')


def t1():
    print('T1 first\n  1')


def _experiment(d, results='T1 first\n  1\nT2 second\n  2\nT10 tenth\n  10\n', passing=True):
    os.makedirs(os.path.join(d, 'tests'))
    os.makedirs(os.path.join(d, 'expected'))
    with open(os.path.join(d, 'tests', 'test_scratch_%d.py' % next(COUNT)), 'w', encoding='utf-8') as f:
        f.write(TEST % passing)
    with open(os.path.join(d, 'expected', 'results.txt'), 'w', encoding='utf-8') as f:
        f.write(results)
    return d


def _run(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = fn(*args)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class HarnessTest(unittest.TestCase):

    def setUp(self):
        self.sections = harness.collect({'t1': t1, 't2': t2, 't10': t10, 'tool': print, 'T3': t1})

    def test_collect_orders_numerically_and_ignores_other_names(self):
        self.assertEqual(list(self.sections), ['T1', 'T2', 'T10'])

    def test_check_passes_on_identical_output(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = _run(harness.check, _experiment(d), self.sections)
        self.assertIsNone(code)
        self.assertIn('identical', out)

    def test_check_reports_the_first_differing_line(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, _ = _run(harness.check, _experiment(d, results='T1 first\n  1\nT2 second\n  9\nT10 tenth\n  10\n'), self.sections)
        self.assertIn('line 4', code)

    def test_check_stops_when_a_test_fails(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, _ = _run(harness.check, _experiment(d, passing=False), self.sections)
        self.assertIn('tests failed', code)

    def test_an_experiment_without_figures(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = _run(harness.figures, _experiment(d), True)
        self.assertIsNone(code)
        self.assertIn('no figures', out)

    def test_main_prints_named_sections(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = _run(harness.main, ['T10', 'T1'], d, self.sections)
        self.assertEqual((code, out), (0, 'T10 tenth\n  10\nT1 first\n  1\n'))

    def test_main_rejects_unknown_sections_and_options(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(_run(harness.main, ['T99'], d, self.sections)[0], 2)
            self.assertEqual(_run(harness.main, ['--fast'], d, self.sections)[0], 2)


if __name__ == '__main__':
    unittest.main()
