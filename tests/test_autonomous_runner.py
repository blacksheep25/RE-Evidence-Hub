import os
import unittest
from unittest import mock

from tests.test_agent_mcp import make_export
from tools.autonomous_naming_runner import LocalModelClient, ModelResponseError, _json_object, run_overnight
from tools.local_evidence import LocalEvidenceStore


class FakeClient:
    def __init__(self, decision):
        self.decision = decision

    def decide(self, _lookup):
        return self.decision


class AddressAwareClient:
    def decide(self, lookup):
        if lookup["function"]["address"] == "00401000":
            return {"action": "skip", "note": "No grounded naming evidence"}
        return {
            "action": "propose", "name": "Net_Send", "confidence": "high",
            "evidence": ["Calls send"], "evidence_refs": ["send"],
            "rationale": "The direct send import establishes outbound transmission.",
        }


class InvalidThenValidClient:
    def decide(self, lookup):
        if lookup["function"]["address"] == "00401000":
            return {"action": "rename", "name": "InvalidAction"}
        return {"action": "skip", "note": "No grounded naming evidence"}


class ProviderFailureClient:
    def decide(self, _lookup):
        raise RuntimeError("provider unavailable")


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


class AutonomousRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = make_export()
        self.addCleanup(self.temporary.cleanup)

    def test_json_response_accepts_fenced_payload(self):
        self.assertEqual("skip", _json_object('```json\n{"action":"skip"}\n```')["action"])

    def test_run_writes_candidate_not_annotation(self):
        store = LocalEvidenceStore(self.temporary.name)
        result = run_overnight(store, AddressAwareClient(), "runner-test", max_targets=2)
        self.assertEqual(1, result["proposed"])
        self.assertTrue(os.path.isfile(os.path.join(self.temporary.name, "agent_runs", "runner-test", "name_candidates.json")))
        self.assertFalse(os.path.exists(os.path.join(self.temporary.name, "annotations", "function_names.json")))

    def test_dry_run_performs_no_writes(self):
        store = LocalEvidenceStore(self.temporary.name)
        result = run_overnight(store, FakeClient({"action": "skip", "note": "unclear"}), "dry", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse(os.path.exists(os.path.join(self.temporary.name, "agent_runs")))

    def test_invalid_decisions_are_retired_without_stopping_the_run(self):
        store = LocalEvidenceStore(self.temporary.name)
        result = run_overnight(store, InvalidThenValidClient(), "invalid-test", max_targets=4)
        self.assertEqual(4, result["processed"])
        self.assertEqual(3, result["invalid_decisions"])
        self.assertEqual(0, result["fatal_errors"])
        self.assertEqual(1, result["skipped"])
        with open(os.path.join(self.temporary.name, "agent_runs", "invalid-test", "runner.jsonl"), encoding="utf-8") as handle:
            self.assertEqual(3, sum('"event": "invalid-decision"' in line for line in handle))

    def test_provider_failure_still_stops_safely(self):
        store = LocalEvidenceStore(self.temporary.name)
        result = run_overnight(store, ProviderFailureClient(), "provider-test", max_targets=2)
        self.assertEqual(0, result["processed"])
        self.assertEqual(1, result["fatal_errors"])

    @mock.patch("tools.autonomous_naming_runner.requests.post")
    def test_openai_compatible_response(self, post):
        post.return_value = FakeResponse({"choices": [{"message": {"content": '{"action":"skip","note":"unclear"}'}}]})
        decision = LocalModelClient("http://local/v1/chat/completions", "fixture", retries=0).decide({"function": {"address": "1"}})
        self.assertEqual("skip", decision["action"])

    @mock.patch("tools.autonomous_naming_runner.requests.post")
    def test_ollama_native_response(self, post):
        post.return_value = FakeResponse({"message": {"content": '{"action":"defer","note":"needs caller"}'}})
        decision = LocalModelClient("http://local/api/chat", "fixture", provider="ollama", retries=0).decide({"function": {"address": "1"}})
        self.assertEqual("defer", decision["action"])
        self.assertEqual("json", post.call_args.kwargs["json"]["format"])

    @mock.patch("tools.autonomous_naming_runner.requests.post")
    def test_malformed_model_output_is_distinct_from_provider_failure(self, post):
        post.return_value = FakeResponse({"message": {"content": "not json"}})
        with self.assertRaises(ModelResponseError):
            LocalModelClient("http://local/api/chat", "fixture", provider="ollama", retries=0).decide({})
