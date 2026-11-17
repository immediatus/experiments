"""lint runs ruff when it is installed and otherwise a standard-library check that catches unused imports and
imports of another module's private names."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import lint  # noqa: E402


def _check(source):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'm.py')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(source)
        return lint.fallback([path])


class LintTest(unittest.TestCase):

    def test_clean_module_passes(self):
        self.assertEqual(_check('import math\n\nprint(math.pi)\n'), [])

    def test_unused_import_fails(self):
        self.assertTrue(any('unused import os' in e for e in _check('import os\nimport math\n\nprint(math.pi)\n')))

    def test_unused_from_import_fails(self):
        self.assertTrue(any('unused import floor' in e for e in _check('from math import floor, pi\n\nprint(pi)\n')))

    def test_private_import_fails(self):
        self.assertTrue(any('private name _helper' in e for e in _check('from other import _helper\n\n_helper()\n')))

    def test_open_without_encoding_fails(self):
        self.assertTrue(any('encoding' in e for e in _check('data = open("x.txt").read()\n')))

    def test_binary_open_and_explicit_encoding_pass(self):
        self.assertEqual(_check('a = open("x", "rb")\nb = open("y", encoding="utf-8")\n'), [])

    def test_reexport_marked_noqa_passes(self):
        self.assertEqual(_check('from math import (  # noqa: F401\n    floor, pi)\n'), [])

    def test_name_used_only_in_a_string_annotation_is_used(self):
        self.assertEqual(_check('import typing\n\nx: "typing.Any" = 1\n'), [])


if __name__ == '__main__':
    unittest.main()
