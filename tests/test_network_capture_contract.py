import json
import os
import tempfile
import unittest

from tools.network_capture import build_capture, save_capture
from tools.network_reconstruction import build_report
from tools.protocol_contract import build_contract, validate_contract


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "samples", "tiny_export")


class NetworkCaptureContractTests(unittest.TestCase):
    def test_import_runtime_frames_and_surface_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = os.path.join(temporary, "capture.jsonl")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"direction": "tx", "transport": "tcp", "remote_address": "127.0.0.1", "remote_port": 15779, "payload_hex": "01 02 03"}) + "\n")
            capture = build_capture(SAMPLE, source, "authorised fixture")
            self.assertEqual(3, capture["summary"]["payload_bytes"])
            output = os.path.join(temporary, "export", "derived", "network", "runtime_capture.json")
            os.makedirs(os.path.join(temporary, "export"), exist_ok=True)
            save_capture(SAMPLE, capture, output)
            self.assertTrue(os.path.isfile(output))

    def test_protocol_contract_requires_evidence_for_confirmed_sections(self):
        contract = build_contract(SAMPLE)
        self.assertEqual([], validate_contract(contract))
        contract["sections"]["framing"]["status"] = "confirmed"
        errors = validate_contract(contract)
        self.assertTrue(any("confirmed framing requires" in error for error in errors))

    def test_static_report_has_runtime_capture_slot(self):
        self.assertIn("runtime_capture", build_report(SAMPLE))
