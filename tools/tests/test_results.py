"""results reads a results file into its sections, rows, cells and numbers."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import results  # noqa: E402

TEXT = 'T1 first: a | b\n   3x | 1,836 s\n\n  10x | 3.17x\nT10 tenth\n  7\nT2 second\n'


class ResultsTest(unittest.TestCase):

    def test_sections_in_file_order_with_their_headers(self):
        blocks = results.parse(TEXT)
        self.assertEqual(list(blocks), ['T1', 'T10', 'T2'])
        self.assertTrue(blocks['T10'].startswith('T10 tenth'))

    def test_a_name_is_not_a_prefix_of_another(self):
        self.assertEqual(results.rows(results.parse(TEXT)['T1']), ['3x | 1,836 s', '10x | 3.17x'])

    def test_a_section_with_no_rows(self):
        self.assertEqual(results.rows(results.parse(TEXT)['T2']), [])

    def test_cells_and_numbers(self):
        self.assertEqual(results.cells('3x | 1,836 s'), ['3x', '1,836 s'])
        self.assertEqual(results.number('1,836 s'), 1836.0)
        self.assertEqual(results.number('3.17x'), 3.17)

    def test_text_before_the_first_header_is_ignored(self):
        self.assertEqual(list(results.parse('preamble\nT1 only\n  1\n')), ['T1'])


if __name__ == '__main__':
    unittest.main()
