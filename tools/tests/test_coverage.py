"""coverage measures which lines of an experiment's model/ its own tests execute."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import coverage  # noqa: E402

MODEL = '''"""A model."""


def tested(x):
    """Doubled."""
    return 2 * x


def untested(x):
    y = x + 1
    return y
'''

TEST = '''import os
import sys
import unittest
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')]
import m


class T(unittest.TestCase):
    def test_tested(self):
        self.assertEqual(m.tested(2), 4)
'''


class CoverageTest(unittest.TestCase):

    def test_reports_each_model_file(self):
        with tempfile.TemporaryDirectory() as d:
            for sub, name, text in (('model', 'm.py', MODEL), ('tests', 'test_m.py', TEST)):
                os.makedirs(os.path.join(d, sub), exist_ok=True)
                with open(os.path.join(d, sub, name), 'w', encoding='utf-8') as f:
                    f.write(text)
            report = coverage.measure(d)
        self.assertEqual(set(report), {'model/m.py'})
        run, total = report['model/m.py']
        self.assertEqual(total, 5)
        self.assertEqual(run, 3)

    def test_executable_lines_skip_docstrings(self):
        lines = coverage.executable_lines('def f():\n    """Doc."""\n    return 1\n')
        self.assertEqual(lines, {1, 3})


if __name__ == '__main__':
    unittest.main()
