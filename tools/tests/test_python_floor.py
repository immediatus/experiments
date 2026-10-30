"""Every Python file in the repository parses under the oldest supported version, 3.10."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import python_floor  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


class PythonFloorTest(unittest.TestCase):

    def test_repository_parses_under_3_10(self):
        self.assertEqual(python_floor.incompatible(ROOT), [])

    def test_a_3_11_construct_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'new.py'), 'w', encoding='utf-8') as f:
                f.write('try:\n    pass\nexcept* ValueError:\n    pass\n')
            self.assertEqual([os.path.basename(p) for p, _ in python_floor.incompatible(d)], ['new.py'])


if __name__ == '__main__':
    unittest.main()
