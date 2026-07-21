import json
import os
import tempfile
import unittest

from tools.build_local_index import build
from tools.build_class_registry import build_registry, save_registry
from tools.build_name_review_queue import build_review_queue, save_review_queue
from tools.analysis_tools import AnalysisTools
from tools.evidence_tools import EvidenceTools, build_parser, run_command
from tools.local_evidence import EvidenceError, LocalEvidenceStore
from binary_agent_server import _validate_bind, create_app


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle)


def write_text(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


class LocalEvidenceStoreTests(unittest.TestCase):
    def make_export(self):
        temporary = tempfile.TemporaryDirectory()
        root = temporary.name
        write_json(os.path.join(root, "manifest.json"), {
            "binary": {"name": "fixture.exe", "image_base": "00400000"},
            "language": {"id": "x86:LE:32:default"},
            "functions": {"count": 2},
        })
        write_json(os.path.join(root, "index.json"), {
            "version": 2,
            "functions": {
                "00401000": {"address": "00401000", "name": "FUN_00401000", "file": "functions/00401000.json"},
                "00402000": {"address": "00402000", "name": "FUN_00402000", "file": "functions/00402000.json"},
            },
            "function_names": {"FUN_00401000": ["00401000"], "FUN_00402000": ["00402000"]},
        })
        write_json(os.path.join(root, "functions", "00401000.json"), {
            "address": "00401000", "name": "FUN_00401000", "namespace": "", "signature": "void FUN_00401000(void)",
            "hash": "a", "range": {}, "size": 12, "instruction_count": 3, "parameters": [], "locals": [],
            "assembly": "CALL 00402000", "decompiler": {"success": True, "c_code": "load login_panel.asset;"},
            "calls": [{"address": "00402000", "name": "FUN_00402000"}], "called_by": [], "comments": [], "xrefs": [],
        })
        write_json(os.path.join(root, "functions", "00402000.json"), {
            "address": "00402000", "name": "FUN_00402000", "namespace": "", "signature": "void FUN_00402000(void)",
            "hash": "b", "range": {}, "size": 8, "instruction_count": 2, "parameters": [], "locals": [],
            "assembly": "RET", "decompiler": {"success": True, "c_code": "return;"},
            "calls": [], "called_by": [{"address": "00401000", "name": "FUN_00401000"}], "comments": [], "xrefs": [],
        })
        write_json(os.path.join(root, "strings.json"), [{
            "address": "01000000", "value": "interface\\outer\\login_panel.asset",
            "functions": [{"address": "00401000", "name": "FUN_00401000"}],
        }])
        write_json(os.path.join(root, "imports.json"), [{
            "address": "EXTERNAL:1", "name": "send", "library": "WS2_32.DLL",
            "references": [{"address": "00402000", "name": "FUN_00402000"}],
        }])
        write_json(os.path.join(root, "globals.json"), [{
            "address": "00fe4c04", "name": "vftable", "datatype": "pointer[50]", "size": 200,
            "functions": [], "references": [], "value": "None",
        }, {
            "address": "01130470", "name": "", "datatype": "char[20]", "size": 20,
            "functions": [], "references": [], "value": ".?AVCExampleUi@@",
        }])
        write_json(os.path.join(root, "annotations", "function_names.json"), {
            "schema_version": 1, "kind": "ghidra-function-name-overlay", "entries": {
                "00401000": {"active_name": "CExampleUi_ApplyLayout", "decisions": [{
                    "name": "CExampleUi_ApplyLayout", "status": "accepted", "confidence": "high",
                    "evidence": ["The CExampleUi vtable at 00fe4c04 points to this function."], "function_identity": {"assembly_sha256": "a"},
                }]},
            },
        })
        return temporary

    def test_lookup_preserves_raw_data_and_overlays_accepted_name(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        store = LocalEvidenceStore(temporary.name)
        lookup = store.lookup("CExampleUi_ApplyLayout", include_decompiler=False)
        self.assertEqual("FUN_00401000", lookup["function"]["raw_name"])
        self.assertEqual("CExampleUi_ApplyLayout", lookup["function"]["active_name"])
        self.assertEqual("interface\\outer\\login_panel.asset", lookup["evidence"]["strings"][0]["value"])
        self.assertEqual("FUN_00402000", lookup["relationships"]["callees"][0]["raw_name"])
        self.assertIsNone(lookup["relationships"]["callees"][0]["active_name"])

    def test_trace_and_fts_search_are_evidence_backed(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        build(temporary.name)
        store = LocalEvidenceStore(temporary.name)
        trace = store.trace("login_panel.asset", "asset")
        self.assertEqual("00401000", trace["functions_referencing_strings"][0]["address"])
        self.assertTrue(any(item["address"] == "00401000" for item in store.search("login_panel")["results"]))

    def test_fts_body_search_matches_substrings(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        build(temporary.name)
        store = LocalEvidenceStore(temporary.name)
        # "panel" is an infix of the single token "login_panel" in the body; a
        # whole-token index would miss it, the trigram index must find it.
        results = store.search("panel")["results"]
        hit = next((item for item in results if item["address"] == "00401000"), None)
        self.assertIsNotNone(hit)
        self.assertEqual("function-body", hit["match_source"])

    def test_unknown_function_is_an_error(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(EvidenceError):
            LocalEvidenceStore(temporary.name).lookup("missing")

    def test_reload_annotations_refreshes_only_the_overlay(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        store = LocalEvidenceStore(temporary.name)
        overlay_path = os.path.join(temporary.name, "annotations", "function_names.json")
        with open(overlay_path, encoding="utf-8") as handle:
            overlay = json.load(handle)
        overlay["entries"]["00401000"]["active_name"] = "CExampleUi_ReviewedLayout"
        overlay["entries"]["00401000"]["decisions"].append({
            "name": "CExampleUi_ReviewedLayout", "status": "accepted", "confidence": "high",
            "evidence": ["reviewed fixture evidence"], "function_identity": {"assembly_sha256": "a"},
        })
        write_json(overlay_path, overlay)
        store.reload_annotations()
        self.assertEqual("CExampleUi_ReviewedLayout", store.lookup("00401000", include_decompiler=False)["function"]["active_name"])

    def test_class_registry_uses_explicit_annotation_evidence_only(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        registry = build_registry(temporary.name)
        save_registry(temporary.name, registry)
        result = LocalEvidenceStore(temporary.name).class_info("CExampleUi")
        self.assertTrue(result["available"])
        self.assertEqual("CExampleUi_ApplyLayout", result["classes"][0]["accepted_methods"][0]["active_name"])
        self.assertEqual("00fe4c04", result["classes"][0]["vtables"][0]["address"])
        self.assertEqual("01130470", result["classes"][0]["rtti_type_descriptors"][0]["address"])

    def test_review_queue_does_not_promote_suggestions(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        queue = build_review_queue(temporary.name)
        save_review_queue(temporary.name, queue)
        result = LocalEvidenceStore(temporary.name).review_queue("send")
        self.assertTrue(result["available"])
        self.assertEqual("Net_Send", result["candidates"][0]["proposed_name"])
        self.assertEqual("proposed-review-only", result["candidates"][0]["status"])
        self.assertIsNone(LocalEvidenceStore(temporary.name).function("00402000")["analysis"]["active_name"])

    def test_evidence_tools_use_same_store_contract_as_api(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        tools = EvidenceTools(temporary.name)
        result = tools.execute_tool("lookup", {"address": "CExampleUi_ApplyLayout", "include_decompiler": False})
        self.assertEqual("CExampleUi_ApplyLayout", result["function"]["active_name"])
        self.assertEqual("FUN_00401000", result["function"]["raw_name"])
        self.assertTrue(any(item["name"] == "lookup" for item in tools.tool_definitions()))

    def test_evidence_tools_cli_dispatches_to_store(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        args = build_parser().parse_args([
            "--export", temporary.name,
            "lookup", "CExampleUi_ApplyLayout",
            "--no-decompiler",
            "--assembly",
        ])
        result = run_command(args)
        self.assertEqual("CExampleUi_ApplyLayout", result["function"]["active_name"])
        self.assertIn("assembly", result)
        self.assertNotIn("decompiler", result)

    def test_legacy_analysis_tools_wrap_evidence_store(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        tools = AnalysisTools(temporary.name)
        results = tools.search("CExampleUi")
        self.assertEqual("00401000", results[0]["address"])
        self.assertEqual("CExampleUi_ApplyLayout", results[0]["name"])
        self.assertEqual("CExampleUi_ApplyLayout", tools.get_function("00401000")["analysis"]["active_name"])

    def test_http_api_exposes_health_and_route_catalog(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        client = create_app(temporary.name).test_client()
        health = client.get("/health")
        self.assertEqual(200, health.status_code)
        self.assertEqual("online", health.get_json()["status"])
        routes = client.get("/routes")
        self.assertEqual(200, routes.status_code)
        self.assertTrue(any(item["route"] == "/lookup" for item in routes.get_json()["routes"]))

    def test_remote_http_api_requires_explicit_bind_and_bearer_token(self):
        with self.assertRaises(ValueError):
            _validate_bind("0.0.0.0", False, "token")
        with self.assertRaises(ValueError):
            _validate_bind("0.0.0.0", True, "")
        _validate_bind("0.0.0.0", True, "token")
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        client = create_app(temporary.name, remote_token="token").test_client()
        self.assertEqual(401, client.get("/health").status_code)
        self.assertEqual(200, client.get("/health", headers={"Authorization": "Bearer token"}).status_code)

    def test_status_reports_optional_artifact_availability(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        status = LocalEvidenceStore(temporary.name).status()
        self.assertFalse(status["semantic_search"]["available"])
        self.assertFalse(status["runtime_capture"]["available"])

    def test_http_lookup_honours_string_boolean_values(self):
        temporary = self.make_export()
        self.addCleanup(temporary.cleanup)
        client = create_app(temporary.name).test_client()
        response = client.post("/lookup", json={
            "address": "00401000",
            "include_decompiler": "false",
            "include_assembly": "true",
        })
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertNotIn("decompiler", payload)
        self.assertIn("assembly", payload)


class ImportabilityTests(unittest.TestCase):
    def test_start_investigation_is_importable_as_a_module(self):
        # Regression guard: the supported report tool must qualify its sibling
        # imports (from tools.X import ...) so it can be imported as a module,
        # not only run as `python tools/start_investigation.py`.
        import importlib

        module = importlib.import_module("tools.start_investigation")
        self.assertTrue(hasattr(module, "InvestigationRunner"))


if __name__ == "__main__":
    unittest.main()
