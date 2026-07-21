"""Integration tests for the autonomous-agent MCP surface.

Exercises the write/queue tools through the same dispatch an MCP client (e.g.
Hermes) uses: initialize -> tools/list -> tools/call. Covers the evidence
verifier (accept vs. reject a hallucinated ref), resume/skip behavior, and the
capability gate that Hermes requires.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from tools.local_evidence import LocalEvidenceStore
import binary_agent_mcp_server as mcp
from tools import naming_candidates


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle)


def make_export():
    temporary = tempfile.TemporaryDirectory()
    root = temporary.name
    _write(os.path.join(root, "manifest.json"), {
        "binary": {"name": "fixture.exe", "image_base": "00400000"},
        "language": {"id": "x86:LE:32:default"},
        "functions": {"count": 2},
    })
    _write(os.path.join(root, "index.json"), {
        "version": 2,
        "functions": {
            "00401000": {"address": "00401000", "name": "FUN_00401000", "file": "functions/00401000.json"},
            "00402000": {"address": "00402000", "name": "FUN_00402000", "file": "functions/00402000.json"},
        },
        "function_names": {"FUN_00401000": ["00401000"], "FUN_00402000": ["00402000"]},
    })
    _write(os.path.join(root, "functions", "00401000.json"), {
        "address": "00401000", "name": "FUN_00401000", "namespace": "", "signature": "void FUN_00401000(void)",
        "hash": "a", "range": {}, "size": 12, "instruction_count": 3, "parameters": [], "locals": [],
        "assembly": "CALL 00402000", "decompiler": {"success": True, "c_code": "load login_panel.asset;"},
        "calls": [{"address": "00402000", "name": "FUN_00402000"}], "called_by": [], "comments": [], "xrefs": [],
    })
    _write(os.path.join(root, "functions", "00402000.json"), {
        "address": "00402000", "name": "FUN_00402000", "namespace": "", "signature": "void FUN_00402000(void)",
        "hash": "b", "range": {}, "size": 8, "instruction_count": 2, "parameters": [], "locals": [],
        "assembly": "CALL send", "decompiler": {"success": True, "c_code": "return send(s);"},
        "calls": [], "called_by": [{"address": "00401000", "name": "FUN_00401000"}], "comments": [], "xrefs": [],
    })
    _write(os.path.join(root, "strings.json"), [{
        "address": "01000000", "value": "interface\\outer\\login_panel.asset",
        "functions": [{"address": "00401000", "name": "FUN_00401000"}],
    }])
    _write(os.path.join(root, "imports.json"), [
        {
            "address": "EXTERNAL:1", "name": "send", "library": "WS2_32.DLL",
            "references": [{"address": "00402000", "name": "FUN_00402000"}],
        },
        {
            "address": "EXTERNAL:2", "name": "WSASend", "library": "WS2_32.DLL",
            "references": [{"address": "00402000", "name": "FUN_00402000"}],
        },
    ])
    return temporary


def _call(store, name, arguments=None):
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": name, "arguments": arguments or {}}}
    result = mcp.handle(store, message)["result"]
    return json.loads(result["content"][0]["text"]), result.get("isError", False)


class AgentMcpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = make_export()
        self.addCleanup(self.temporary.cleanup)
        self.store = LocalEvidenceStore(self.temporary.name)

    def test_initialize_advertises_tools_capability(self):
        # Hermes skips tools/list (registers zero tools) unless capabilities.tools is non-null.
        result = mcp.handle(self.store, {"jsonrpc": "2.0", "id": 0, "method": "initialize"})["result"]
        self.assertIsNotNone(result["capabilities"].get("tools"))

    def test_stdio_server_starts_from_foreign_cwd_with_stripped_environment(self):
        script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "binary_agent_mcp_server.py")
        with tempfile.TemporaryDirectory() as foreign_cwd:
            process = subprocess.run(
                [sys.executable, os.path.abspath(script), "--export", self.temporary.name],
                input=json.dumps({"jsonrpc": "2.0", "id": 7, "method": "initialize"}) + "\n",
                text=True,
                capture_output=True,
                cwd=foreign_cwd,
                env={"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows")},
                timeout=15,
            )
        self.assertEqual(0, process.returncode, process.stderr)
        response = json.loads(process.stdout.strip())
        self.assertEqual(7, response["id"])
        self.assertIn("tools", response["result"]["capabilities"])

    def test_tools_list_includes_write_and_queue_tools(self):
        result = mcp.handle(self.store, {"jsonrpc": "2.0", "id": 0, "method": "tools/list"})["result"]
        tools = {t["name"]: t for t in result["tools"]}
        names = set(tools)
        self.assertTrue({"binary_annotate", "binary_propose_name", "binary_candidate_queue", "binary_candidate_page", "binary_candidate_preflight", "binary_review_brief", "binary_review_candidate", "binary_next_target", "binary_progress", "binary_network_map"} <= names)
        schema = tools["binary_annotate"]["inputSchema"]
        self.assertEqual(["medium", "high"], schema["properties"]["confidence"]["enum"])
        self.assertTrue({"evidence", "rationale", "evidence_refs"} <= set(schema["required"]))

    def test_network_map_is_available_to_agents_without_writing(self):
        payload, failed = _call(self.store, "binary_network_map", {"limit": 25})
        self.assertFalse(failed)
        self.assertTrue(payload["stages"]["send"]["observed"])
        self.assertFalse(os.path.exists(os.path.join(self.temporary.name, "derived")))

    def test_unattended_candidate_is_isolated_until_reviewed(self):
        self.store.agent_run_id = "night-01"
        payload, failed = _call(self.store, "binary_propose_name", {
            "address": "00402000", "name": "Net_Send", "confidence": "high",
            "evidence": ["Calls the send import"], "evidence_refs": ["send"],
            "rationale": "The direct send import establishes network transmit behavior.",
        })
        self.assertFalse(failed)
        self.assertTrue(payload["accepted"])
        self.assertFalse(payload["promoted"])
        self.assertIsNone(self.store.lookup("00402000", include_decompiler=False)["function"]["active_name"])
        self.assertFalse(os.path.exists(os.path.join(self.temporary.name, "annotations", "function_names.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.temporary.name, "agent_runs", "night-01", "name_candidates.json")))

        queue, _ = _call(self.store, "binary_candidate_queue")
        self.assertEqual(1, queue["count"])
        reviewed, _ = _call(self.store, "binary_review_candidate", {
            "address": "00402000", "action": "accept", "note": "verified by stronger model",
        })
        self.assertEqual("accepted", reviewed["candidate_status"])
        self.assertEqual("Net_Send", self.store.lookup("00402000", include_decompiler=False)["function"]["active_name"])

    def test_candidate_page_is_bounded_and_uses_a_stable_cursor(self):
        self.store.agent_run_id = "night-page"
        for address, name, refs in (
            ("00401000", "UI_LoginPanel", ["interface\\outer\\login_panel.asset"]),
            ("00402000", "Net_Send", ["send"]),
        ):
            lookup = self.store.lookup(address, include_decompiler=False)
            naming_candidates.propose(self.temporary.name, "night-page", lookup, {
                "name": name, "confidence": "high", "evidence": refs,
                "evidence_refs": refs, "rationale": "Fixture candidate for paginated review coverage.",
            })
        first, failed = _call(self.store, "binary_candidate_page", {"limit": 1})
        self.assertFalse(failed)
        self.assertEqual(2, first["total_count"])
        self.assertEqual(1, first["returned_count"])
        self.assertTrue(first["next_cursor"])
        self.assertIn("triage_warning", first)
        second, failed = _call(self.store, "binary_candidate_page", {"limit": 1, "cursor": first["next_cursor"]})
        self.assertFalse(failed)
        self.assertEqual(1, second["returned_count"])
        self.assertNotEqual(first["candidates"][0]["address"], second["candidates"][0]["address"])
        invalid, failed = _call(self.store, "binary_candidate_page", {"cursor": "not-a-cursor"})
        self.assertTrue(failed)
        self.assertIn("Invalid candidate-page cursor", invalid["error"])

    def test_lookup_can_cap_decompiler_text(self):
        payload, failed = _call(self.store, "binary_lookup", {"address": "00401000", "max_decompiler_chars": 5})
        self.assertFalse(failed)
        self.assertEqual("load ", payload["decompiler"]["c_code"])
        self.assertTrue(payload["decompiler"]["c_code_truncated"])
        self.assertEqual(len("load login_panel.asset;"), payload["decompiler"]["original_c_code_chars"])

    def test_preflight_brief_and_deferred_review_preserve_candidate(self):
        self.store.agent_run_id = "night-preflight"
        proposed, failed = _call(self.store, "binary_propose_name", {
            "address": "00402000", "name": "Net_Send", "confidence": "high",
            "evidence": ["Calls the send import"], "evidence_refs": ["send"],
            "rationale": "The direct send import establishes network transmit behavior.",
        })
        self.assertFalse(failed)
        self.assertTrue(proposed["accepted"])
        preflight, failed = _call(self.store, "binary_candidate_preflight")
        self.assertFalse(failed)
        self.assertEqual(1, preflight["summary"]["candidate_count"])
        self.assertEqual(1, preflight["summary"]["buckets"]["review"])
        page, failed = _call(self.store, "binary_candidate_page", {"bucket": "review"})
        self.assertFalse(failed)
        self.assertEqual(1, page["returned_count"])
        brief, failed = _call(self.store, "binary_review_brief", {"address": "00402000", "max_decompiler_chars": 4})
        self.assertFalse(failed)
        self.assertTrue(brief["grounding"]["all_refs_grounded"])
        self.assertIn("send", brief["grounding"]["matched_raw_values"])
        self.assertTrue(brief["decompiler"]["c_code_truncated"])
        deferred, failed = _call(self.store, "binary_review_candidate", {"address": "00402000", "action": "defer", "note": "Needs packet caller context"})
        self.assertFalse(failed)
        self.assertEqual("deferred", deferred["candidate_status"])
        self.assertIsNone(self.store.lookup("00402000", include_decompiler=False)["function"]["active_name"])
        deferred_page, failed = _call(self.store, "binary_candidate_page", {"status": "deferred", "bucket": "review"})
        self.assertFalse(failed)
        self.assertEqual(1, deferred_page["total_count"])

    def test_candidate_rejection_never_promotes(self):
        self.store.agent_run_id = "night-reject"
        _call(self.store, "binary_propose_name", {
            "address": "00402000", "name": "Net_Send", "confidence": "medium",
            "evidence": ["Calls the send import"], "evidence_refs": ["send"],
            "rationale": "The send import supports a transmit-related candidate.",
        })
        reviewed, _ = _call(self.store, "binary_review_candidate", {"address": "00402000", "action": "reject"})
        self.assertEqual("rejected", reviewed["candidate_status"])
        self.assertIsNone(self.store.lookup("00402000", include_decompiler=False)["function"]["active_name"])

    def test_tampered_candidate_is_revalidated_at_review(self):
        self.store.agent_run_id = "night-tamper"
        _call(self.store, "binary_propose_name", {
            "address": "00402000", "name": "Net_Send", "confidence": "medium",
            "evidence": ["Calls send"], "evidence_refs": ["send"],
            "rationale": "The send import supports the proposed transmit behavior.",
        })
        path = os.path.join(self.temporary.name, "agent_runs", "night-tamper", "name_candidates.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        data["entries"]["00402000"]["proposed_name"] = "DeleteAccount"
        _write(path, data)
        payload, failed = _call(self.store, "binary_review_candidate", {"address": "00402000", "action": "accept"})
        self.assertTrue(failed)
        self.assertIn("review policy", payload["error"])
        self.assertIsNone(self.store.lookup("00402000", include_decompiler=False)["function"]["active_name"])

    def test_guarded_annotate_accepts_grounded_evidence_and_persists(self):
        payload, _ = _call(self.store, "binary_annotate", {
            "address": "00402000", "name": "Net_Send", "confidence": "high",
            "evidence": ["Calls the send import"], "evidence_refs": ["send"],
            "rationale": "The direct send import establishes network transmit behavior.",
            "reviewer": "test-reviewer",
        })
        self.assertTrue(payload["accepted"])
        # Visible in the same session (reload happened) and durable on disk.
        self.assertEqual("Net_Send", self.store.lookup("00402000", include_decompiler=False)["function"]["active_name"])
        with open(os.path.join(self.temporary.name, "annotations", "function_names.json"), encoding="utf-8") as handle:
            overlay = json.load(handle)
        self.assertEqual("Net_Send", overlay["entries"]["00402000"]["active_name"])
        self.assertEqual("test-reviewer", overlay["entries"]["00402000"]["decisions"][0]["reviewer"])
        self.assertFalse(any(name.startswith(".annotations-") for name in os.listdir(os.path.join(self.temporary.name, "annotations"))))

    def test_guarded_annotate_rejects_hallucinated_evidence(self):
        payload, _ = _call(self.store, "binary_annotate", {
            "address": "00402000", "name": "Bogus", "confidence": "high",
            "evidence_refs": ["this_token_is_not_in_the_function"],
        })
        self.assertFalse(payload["accepted"])
        self.assertIn("this_token_is_not_in_the_function", payload["missing_refs"])
        # Nothing was written.
        self.assertFalse(os.path.exists(os.path.join(self.temporary.name, "annotations", "function_names.json")))

    def test_next_target_then_skip_after_annotation(self):
        first = _call(self.store, "binary_next_target")[0]
        self.assertIn(first["address"], ("00401000", "00402000"))
        # Annotate 00402000 with grounded evidence; the queue must then skip it.
        _call(self.store, "binary_annotate", {
            "address": "00402000", "name": "Net_Send", "confidence": "medium", "evidence_refs": ["send"],
            "evidence": ["Calls the send import"],
            "rationale": "The direct send import establishes network transmit behavior.",
        })
        remaining = []
        target = _call(self.store, "binary_next_target")[0]
        while not target.get("exhausted"):
            remaining.append(target["address"])
            _call(self.store, "binary_progress", {"address": target["address"], "status": "skipped", "note": "test"})
            target = _call(self.store, "binary_next_target")[0]
        self.assertNotIn("00402000", remaining)  # annotated -> never re-served

    def test_progress_summary_and_status(self):
        summary = _call(self.store, "binary_progress")[0]["summary"]
        self.assertEqual(2, summary["total_functions"])
        status = _call(self.store, "binary_status")[0]
        self.assertIn("progress", status)

    def test_annotate_accepts_function_name_input(self):
        # The write path must accept a function name (like binary_lookup does),
        # resolving it to the same canonical address the verifier used.
        payload, _ = _call(self.store, "binary_annotate", {
            "address": "FUN_00402000", "name": "Net_Send", "confidence": "medium", "evidence_refs": ["send"],
            "evidence": ["Calls the send import"],
            "rationale": "The direct send import establishes network transmit behavior.",
        })
        self.assertTrue(payload["accepted"])
        self.assertEqual("00402000", payload["address"])

    def test_guard_rejects_empty_malformed_and_unlinked_names(self):
        common = {
            "address": "00402000",
            "confidence": "high",
            "evidence": ["Calls the send import"],
            "evidence_refs": ["send"],
            "rationale": "The direct send import establishes network transmit behavior.",
        }
        for name in ("", "bad name", "FUN_00402000", "DeleteAccount"):
            payload, _ = _call(self.store, "binary_annotate", dict(common, name=name))
            self.assertFalse(payload["accepted"], name)
        self.assertFalse(os.path.exists(os.path.join(self.temporary.name, "annotations", "function_names.json")))

    def test_two_grounded_refs_allow_a_semantic_name(self):
        payload, _ = _call(self.store, "binary_annotate", {
            "address": "00402000", "name": "Net_TransmitBuffer", "confidence": "medium",
            "evidence": ["Calls both send and WSASend imports"],
            "evidence_refs": ["send", "WSASend"],
            "rationale": "Two independent send APIs establish outbound buffer transmission.",
        })
        self.assertTrue(payload["accepted"])

    def test_progress_unknown_address_is_a_tool_error(self):
        payload, is_error = _call(self.store, "binary_progress", {"address": "nope", "status": "skipped"})
        self.assertTrue(is_error)
        self.assertIn("error", payload)

    def test_repeated_failed_annotation_retires_target(self):
        # Repeated ungrounded attempts on the same target are counted and the
        # target is eventually dropped from the frontier (no dead loop).
        for _ in range(3):
            payload, _ = _call(self.store, "binary_annotate", {
                "address": "00401000", "name": "Guess", "confidence": "low", "evidence_refs": ["totally_absent_token"],
            })
            self.assertFalse(payload["accepted"])
        # 00401000 has been deferred MAX_ATTEMPTS times -> next_target must skip it.
        seen = set()
        target = _call(self.store, "binary_next_target")[0]
        while not target.get("exhausted"):
            seen.add(target["address"])
            _call(self.store, "binary_progress", {"address": target["address"], "status": "skipped"})
            target = _call(self.store, "binary_next_target")[0]
        self.assertNotIn("00401000", seen)


if __name__ == "__main__":
    unittest.main()
