import os
import tempfile
import unittest

from tools.public_release_check import findings, path_finding


class PublicReleaseCheckTests(unittest.TestCase):
    def test_blocks_export_paths_and_target_artifacts(self):
        self.assertEqual("tracked target/export path", path_finding("project_exports/target/functions/00401000.json"))
        self.assertEqual("tracked binary, database, archive, or debug artifact", path_finding("target.exe"))
        self.assertEqual("", path_finding("project_exports/README.md"))

    def test_flags_obvious_secret_but_allows_source_text(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "clean.py"), "w", encoding="utf-8") as handle:
                handle.write("token = os.environ.get('TOKEN')\n")
            with open(os.path.join(root, "secret.txt"), "w", encoding="utf-8") as handle:
                handle.write("ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJ")
            result = findings(["clean.py", "secret.txt"], root)
        self.assertEqual(["secret.txt: possible secret"], result)
