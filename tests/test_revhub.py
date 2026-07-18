"""Tests for the revhub CLI: current-export pointer precedence and the doctor.

The pointer lives in a user config dir; these tests redirect that dir to a temp
location (via APPDATA on Windows and XDG_CONFIG_HOME elsewhere) so they never
touch or depend on the developer's real pointer.
"""

import os
import tempfile
import unittest

import host_config
import revhub_cli
from project_layout import project_export_path, safe_project_name


class ExportPrecedenceTests(unittest.TestCase):
    def setUp(self):
        self._saved_env = dict(os.environ)
        self._tmp = tempfile.TemporaryDirectory()
        # Redirect the config dir on both platforms and clear the env override.
        os.environ["APPDATA"] = self._tmp.name
        os.environ["XDG_CONFIG_HOME"] = self._tmp.name
        os.environ.pop("GHIDRA_AI_EXPORT_PATH", None)
        host_config.clear_current_export()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        self._tmp.cleanup()

    def test_default_when_nothing_set(self):
        path, source = host_config.resolve_export_source()
        self.assertEqual("built-in default", source)
        self.assertTrue(path.endswith("sample_program.exe"))
        self.assertIn("project_exports", path)

    def test_project_layout_sanitizes_names_and_stays_repo_local(self):
        self.assertEqual("My_Client_.exe", safe_project_name('My Client?.exe'))
        self.assertTrue(project_export_path("client.exe").endswith(os.path.join("project_exports", "client.exe")))

    def test_pointer_beats_default(self):
        host_config.write_current_export("/tmp/example-export")
        path, source = host_config.resolve_export_source()
        self.assertEqual("current-export pointer", source)
        self.assertEqual(os.path.abspath(os.path.expanduser("/tmp/example-export")), path)

    def test_env_beats_pointer(self):
        host_config.write_current_export("/tmp/pointer-export")
        os.environ["GHIDRA_AI_EXPORT_PATH"] = "/tmp/env-export"
        path, source = host_config.resolve_export_source()
        self.assertEqual("GHIDRA_AI_EXPORT_PATH env", source)
        self.assertEqual("/tmp/env-export", path)

    def test_explicit_beats_everything(self):
        host_config.write_current_export("/tmp/pointer-export")
        os.environ["GHIDRA_AI_EXPORT_PATH"] = "/tmp/env-export"
        path, source = host_config.resolve_export_source("/tmp/explicit-export")
        self.assertEqual("argument", source)
        self.assertEqual("/tmp/explicit-export", path)

    def test_clear_removes_pointer(self):
        host_config.write_current_export("/tmp/pointer-export")
        self.assertTrue(host_config.clear_current_export())
        self.assertIsNone(host_config.read_current_export())
        # Clearing again reports nothing to remove.
        self.assertFalse(host_config.clear_current_export())


class DoctorTests(unittest.TestCase):
    def test_python_check_passes_and_missing_export_warns(self):
        missing = os.path.join(tempfile.gettempdir(), "revhub-doctor-no-such-export")
        checks = revhub_cli._collect_doctor(missing)

        by_name = {name: (status, detail) for (name, status, detail, cat) in checks}
        self.assertIn("python", by_name)
        self.assertEqual("PASS", by_name["python"][0])

        # The active export does not exist -> a WARN in the export category.
        export_checks = [c for c in checks if c[3] == "export"]
        self.assertTrue(any(c[1] == "WARN" for c in export_checks))
        # Nothing in the baseline category should be a hard failure in a test env
        # that can import this module (baseline deps are importable).
        baseline = [c for c in checks if c[3] == "baseline"]
        self.assertTrue(baseline)

    def test_first_positional_is_option_value_aware(self):
        fp = revhub_cli._first_positional
        # No positional -> None (active export gets injected).
        self.assertIsNone(fp([], {"--output"}))
        self.assertIsNone(fp(["--full"], set()))
        self.assertIsNone(fp(["--output", "out.db"], {"--output"}))  # value not a path
        self.assertIsNone(fp(["--output=out.db"], {"--output"}))
        self.assertIsNone(fp(["--limit", "50"], {"--limit"}))
        self.assertIsNone(fp(["--limit", "-5"], {"--limit"}))
        # A real positional is detected regardless of surrounding options.
        self.assertEqual("/some/export", fp(["/some/export"], {"--output"}))
        self.assertEqual("/some/export", fp(["--full", "/some/export"], set()))
        self.assertEqual("/some/export", fp(["--output", "out.db", "/some/export"], {"--output"}))

    def test_positionals_support_two_path_delegates(self):
        values = revhub_cli._positionals
        self.assertEqual(["capture.jsonl"], values(["--source", "night", "capture.jsonl"], {"--source"}))
        self.assertEqual(["export", "capture.jsonl"], values(["export", "capture.jsonl"], {"--source"}))


if __name__ == "__main__":
    unittest.main()
