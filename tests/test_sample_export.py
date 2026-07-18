"""Guard the checked-in sample export against bit-rot.

The sample under samples/tiny_export is what the README, docs, and CI use for a
Ghidra-free first run. This test proves it stays structurally valid and
queryable through the same LocalEvidenceStore core as the HTTP/MCP adapters.
"""

import os
import unittest

from tools.local_evidence import LocalEvidenceStore


SAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "samples",
    "tiny_export",
)


class SampleExportTests(unittest.TestCase):
    def test_sample_export_overlays_accepted_name(self):
        store = LocalEvidenceStore(SAMPLE)
        lookup = store.lookup("CPSTitle_ApplyLayout", include_decompiler=False)
        self.assertEqual("FUN_00401000", lookup["function"]["raw_name"])
        self.assertEqual("CPSTitle_ApplyLayout", lookup["function"]["active_name"])

    def test_sample_export_preserves_relationships_and_evidence(self):
        store = LocalEvidenceStore(SAMPLE)
        lookup = store.lookup("00401000", include_decompiler=False)
        self.assertEqual("FUN_00402000", lookup["relationships"]["callees"][0]["raw_name"])
        self.assertEqual(
            "interface\\outer\\login_panel.asset",
            lookup["evidence"]["strings"][0]["value"],
        )


if __name__ == "__main__":
    unittest.main()
