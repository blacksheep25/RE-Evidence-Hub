"""Unit tests for the evidence verifier that guards autonomous annotations.

Regression coverage for the review that found the original substring-over-whole-
bundle check would rubber-stamp any name from a single ubiquitous token.
"""

import unittest

from tools.agent_evidence import validate_annotation_proposal, verify_evidence_refs


def lookup(imports=(), strings=(), callees=()):
    return {
        "evidence": {
            "imports": [{"name": n} for n in imports],
            "strings": [{"value": v} for v in strings],
        },
        "relationships": {
            "callees": [{"raw_name": c, "active_name": None} for c in callees],
            "callers": [],
        },
    }


class VerifierTests(unittest.TestCase):
    def test_accepts_grounded_import_string_and_callee(self):
        lk = lookup(imports=["WSARecv"], strings=["interface\\outer\\login_panel.asset"], callees=["Net_Send"])
        self.assertEqual((True, []), verify_evidence_refs(lk, ["WSARecv"]))
        self.assertEqual((True, []), verify_evidence_refs(lk, ["login_panel"]))  # whole token inside a string value
        self.assertEqual((True, []), verify_evidence_refs(lk, ["Net_Send"]))

    def test_rejects_generic_and_decompiler_and_asm_tokens(self):
        # These appear only in decompiler/assembly/placeholder names, which are NOT checkable.
        lk = lookup(imports=["WSARecv"], strings=["status"], callees=["Net_Send"])
        for bad in ["mov", "param_1", "return", "iVar1", "FUN_00401000", "eax"]:
            ok, _ = verify_evidence_refs(lk, [bad])
            self.assertFalse(ok, "should reject ungrounded token: {}".format(bad))

    def test_rejects_substring_fragment_of_larger_token(self):
        lk = lookup(strings=["config/turkey.ini"])
        ok, missing = verify_evidence_refs(lk, ["key"])
        self.assertFalse(ok)
        self.assertIn("key", missing)

    def test_rejects_too_short_or_empty_refs(self):
        lk = lookup(imports=["ab", "WSARecv"])
        self.assertEqual((False, ["ab"]), verify_evidence_refs(lk, ["ab"]))
        self.assertEqual((False, []), verify_evidence_refs(lk, []))
        self.assertEqual((False, []), verify_evidence_refs(lk, ["   "]))

    def test_one_short_ref_rejects_an_otherwise_grounded_set(self):
        lk = lookup(imports=["WSARecv"])
        self.assertEqual((False, ["ab"]), verify_evidence_refs(lk, ["WSARecv", "ab"]))
        self.assertEqual((False, [""]), verify_evidence_refs(lk, ["WSARecv", "   "]))

    def test_excludes_placeholder_fun_callee_names(self):
        lk = lookup(callees=["FUN_00402000"])
        ok, _ = verify_evidence_refs(lk, ["FUN_00402000"])
        self.assertFalse(ok)

    def test_one_bad_ref_fails_the_whole_citation(self):
        lk = lookup(imports=["WSARecv"])
        ok, missing = verify_evidence_refs(lk, ["WSARecv", "totally_absent"])
        self.assertFalse(ok)
        self.assertEqual(["totally_absent"], missing)

    def test_acceptance_policy_requires_reviewable_name_and_support(self):
        evidence = ["Calls the send import"]
        rationale = "The direct send import establishes transmit behavior."
        self.assertEqual(
            (True, ""),
            validate_annotation_proposal("Net_Send", "high", evidence, rationale, ["send"]),
        )
        for name in ("", "   ", "FUN_00402000", "bad name"):
            self.assertFalse(validate_annotation_proposal(name, "high", evidence, rationale, ["send"])[0])
        self.assertFalse(validate_annotation_proposal("Net_Send", "low", evidence, rationale, ["send"])[0])
        self.assertFalse(validate_annotation_proposal("Net_Send", "high", [], rationale, ["send"])[0])
        self.assertFalse(validate_annotation_proposal("Net_Send", "high", evidence, "short", ["send"])[0])

    def test_unlinked_name_needs_two_independent_refs(self):
        evidence = ["Two independent networking imports are present"]
        rationale = "The pair of imports establishes outbound buffer transmission."
        self.assertFalse(
            validate_annotation_proposal("Net_TransmitBuffer", "medium", evidence, rationale, ["send"])[0]
        )
        self.assertTrue(
            validate_annotation_proposal(
                "Net_TransmitBuffer", "medium", evidence, rationale, ["send", "WSASend"]
            )[0]
        )


if __name__ == "__main__":
    unittest.main()
