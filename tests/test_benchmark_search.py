import os
import unittest

from tools.benchmark_search import benchmark


SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "tiny_export")


class BenchmarkSearchTests(unittest.TestCase):
    def test_sample_benchmark_reports_supported_operations(self):
        result = benchmark(SAMPLE, ["send"], repeats=1)
        self.assertEqual(2, result["function_count"])
        self.assertIn("lookup", result["results"])
        self.assertIn("send", result["results"]["search"])
