"""Regression tests for annotation correction history and export comparison."""

import os
import tempfile
import unittest

from tests.test_agent_mcp import make_export
from tools.export_comparison import compare, main as comparison_main
from tools.function_annotations import annotate, history


class AnnotationHistoryTests(unittest.TestCase):
    def test_replacement_preserves_prior_decision_and_marks_it_superseded(self):
        temporary = make_export()
        self.addCleanup(temporary.cleanup)
        annotate(
            temporary.name, "00402000", "Net_Send", "high", reviewer="alice",
            evidence=["Calls send"], rationale="The send import establishes transmit behaviour.",
        )
        annotate(
            temporary.name, "00402000", "Net_TransmitBuffer", "high", reviewer="bob",
            evidence=["Calls send"], rationale="The send import supports the more specific buffer role.",
        )

        audit = history(temporary.name, "00402000")
        self.assertEqual("Net_TransmitBuffer", audit["active_name"])
        self.assertEqual(2, len(audit["decisions"]))
        first, second = audit["decisions"]
        self.assertEqual("superseded", first["status"])
        self.assertEqual("Net_TransmitBuffer", first["superseded_by"])
        self.assertEqual("alice", first["reviewer"])
        self.assertFalse(first["is_active"])
        self.assertEqual("accepted", second["status"])
        self.assertEqual("bob", second["reviewer"])
        self.assertTrue(second["is_active"])

    def test_history_is_read_only_when_an_export_has_no_overlay(self):
        temporary = make_export()
        self.addCleanup(temporary.cleanup)

        audit = history(temporary.name, "00402000")

        self.assertIsNone(audit["active_name"])
        self.assertEqual([], audit["decisions"])


class ExportComparisonTests(unittest.TestCase):
    def test_same_export_reports_exact_hash_matches_and_no_unlabelled_claims(self):
        temporary = make_export()
        self.addCleanup(temporary.cleanup)

        report = compare(temporary.name, temporary.name, threshold=0.75, limit=10)

        self.assertEqual("re-evidence-export-comparison", report["kind"])
        self.assertEqual(2, report["summary"]["exact_hash_match_count"])
        self.assertIn("leads only", report["confidence_rule"])
        self.assertEqual(2, len(report["exact_hash_matches"]))
        self.assertTrue(all("baseline" in item and "candidate" in item for item in report["exact_hash_matches"]))

    def test_structural_results_are_bounded(self):
        temporary = make_export()
        self.addCleanup(temporary.cleanup)

        report = compare(temporary.name, temporary.name, threshold=0.0, limit=1)

        self.assertLessEqual(len(report["exact_hash_matches"]), 1)
        self.assertLessEqual(len(report["structural_match_leads"]), 1)
        self.assertGreaterEqual(report["summary"]["structural_match_count"], len(report["structural_match_leads"]))

    def test_command_writes_a_rebuildable_report(self):
        temporary = make_export()
        self.addCleanup(temporary.cleanup)
        output_dir = tempfile.TemporaryDirectory()
        self.addCleanup(output_dir.cleanup)
        output = os.path.join(output_dir.name, "comparison.json")

        result = comparison_main([temporary.name, temporary.name, "--output", output])

        self.assertEqual(0, result)
        self.assertTrue(os.path.isfile(output))


if __name__ == "__main__":
    unittest.main()
