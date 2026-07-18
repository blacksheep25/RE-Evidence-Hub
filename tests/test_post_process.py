import json
import shutil
import tempfile
import unittest
from pathlib import Path

from post_process import main


ROOT = Path(__file__).resolve().parents[1]


class PostProcessTests(unittest.TestCase):
    def test_rebuilds_ai_context_without_live_ghidra_program(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "tiny_export"
            shutil.copytree(ROOT / "samples" / "tiny_export", export_path)

            self.assertEqual(main([str(export_path)]), 0)

            context = json.loads((export_path / "ai_context.json").read_text(encoding="utf-8"))
            self.assertEqual(context["binary"]["name"], "sample_program.exe")
            self.assertEqual(context["binary"]["architecture"], "x86:LE:32:default")
            self.assertTrue((export_path / "function_summaries.json").is_file())
            self.assertTrue((export_path / "markdown" / "00401000.md").is_file())


if __name__ == "__main__":
    unittest.main()
