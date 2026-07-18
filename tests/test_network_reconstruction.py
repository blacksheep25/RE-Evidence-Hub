import json
import os
import unittest

from tools.network_reconstruction import build_report, save_report


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "samples", "tiny_export")


class NetworkReconstructionTests(unittest.TestCase):
    def test_sample_maps_network_api_without_inventing_packet_contracts(self):
        report = build_report(SAMPLE)
        self.assertEqual("network-reconstruction-evidence-pack", report["kind"])
        self.assertTrue(report["stages"]["send"]["observed"])
        function = next(item for item in report["functions"] if item["address"] == "00402000")
        self.assertIn("send", function["imports"])
        self.assertIn("packet framing and length rules", report["unresolved_contracts"])

    def test_report_outputs_json_and_markdown(self):
        import tempfile
        with tempfile.TemporaryDirectory() as output:
            paths = save_report(SAMPLE, build_report(SAMPLE), output)
            self.assertTrue(os.path.isfile(paths["json"]))
            self.assertTrue(os.path.isfile(paths["markdown"]))
            with open(paths["json"], encoding="utf-8") as handle:
                self.assertEqual(1, json.load(handle)["schema_version"])
