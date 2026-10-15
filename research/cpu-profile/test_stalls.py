import unittest
from analyze_stalls import union_length

class StallTests(unittest.TestCase):
    def test_overlap_clipping_and_union(self):
        self.assertEqual(union_length([(0, 20), (15, 30), (40, 70)], 10, 50), 30)
    def test_boundary_and_empty_intervals(self):
        self.assertEqual(union_length([(0, 10), (50, 60)], 10, 50), 0)
        self.assertEqual(union_length([], 0, 100), 0)

if __name__ == '__main__':
    unittest.main()
