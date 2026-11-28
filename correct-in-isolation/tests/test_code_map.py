"""Checks that the experiment links every file of its code: each code folder has a README that links every file
in it, and the experiment's README links each of those indexes, so a reader arriving from a claim or from the
README can reach any module, section, test, specification or example by following links.

Run: python3 -m unittest discover -s tests
"""
import glob
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

FOLDERS = {
    'model': ('*.py',),
    'sections': ('*.py',),
    'tests': ('*.py',),
    'audit': ('*.py', '*.json'),
    'tla': ('*.tla', '*.cfg', 'run.py', 'expected.txt'),
    'p': ('**/*.p', 'run.py', 'expected.txt', 'Seams.pproj'),
}


def read(path):
    """The text of a file under the experiment, as UTF-8."""
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


class CodeMap(unittest.TestCase):
    """Every file is linked from its folder readme; the readme links every index."""

    def test_every_file_is_linked_from_its_folder_readme(self):
        for folder, patterns in FOLDERS.items():
            index = read(os.path.join(folder, 'README.md'))
            for pattern in patterns:
                for path in glob.glob(os.path.join(ROOT, folder, pattern), recursive=True):
                    rel = os.path.relpath(path, os.path.join(ROOT, folder)).replace(os.sep, '/')
                    with self.subTest(file='%s/%s' % (folder, rel)):
                        self.assertIn('](%s)' % rel, index)

    def test_the_readme_links_every_index(self):
        readme = read('README.md')
        for folder in FOLDERS:
            with self.subTest(folder=folder):
                self.assertIn('](%s/README.md)' % folder, readme)


if __name__ == '__main__':
    unittest.main()
