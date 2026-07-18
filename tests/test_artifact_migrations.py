import json
import os
import tempfile
import unittest

from tools.migrate_artifacts import audit, migrate


class ArtifactMigrationTests(unittest.TestCase):
    def test_legacy_progress_is_backed_up_and_migrated(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "agent_runs", "old", "investigation_progress.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"entries": {}}, handle)
            before = audit(root)
            self.assertEqual(1, before["unsupported"])
            result = migrate(root)
            self.assertEqual(1, len(result["changed"]))
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(1, json.load(handle)["schema_version"])
            self.assertEqual(0, audit(root)["unsupported"])
