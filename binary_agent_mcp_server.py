"""Dependency-free stdio MCP adapter for the local evidence store.

Run this process from an MCP-capable client. Most tools are read-only, evidence-
backed retrieval. The exceptions support autonomous, resumable investigation and
never touch the Ghidra database or the raw export files:

- ``binary_propose_name`` records unattended output only in an isolated run.
- ``binary_review_candidate`` explicitly promotes or rejects a proposal.
- ``binary_annotate`` records a confirmed name only in the reversible annotation
  overlay (``annotations/``), and only after the cited evidence is verified to
  appear in that function's own bundle.
- ``binary_progress`` / ``binary_next_target`` read and update the resumable work
  ledger (``investigation_progress.json``).

See docs/autonomous-agent.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# MCP clients (e.g. Hermes) spawn stdio servers with a stripped environment and
# an unspecified working directory, so make the repository importable regardless
# of how we were launched, before importing any sibling modules.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from host_config import DEFAULT_EXPORT_PATH
from tools.local_evidence import EvidenceError, LocalEvidenceStore
from tools.function_annotations import annotate
from tools.agent_evidence import validate_annotation_proposal, verify_evidence_refs
from tools import investigation_ledger as ledger
from tools import naming_candidates
from tools.network_reconstruction import build_report as build_network_report


SERVER_INFO = {"name": "binary-local-evidence", "version": "1.2.0"}

TOOLS = [
    {
        "name": "binary_status",
        "description": "Get the active local export identity and available local search capabilities.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "binary_search",
        "description": "Search raw function metadata, accepted evidence-backed names, and the optional local FTS index.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}},
            "required": ["query"],
        },
    },
    {
        "name": "binary_lookup",
        "description": "Return one function with accepted annotations, strings/imports, callers, callees, and optional decompiler/assembly evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Function address or an unambiguous exact function name."},
                "include_decompiler": {"type": "boolean", "default": True},
                "include_assembly": {"type": "boolean", "default": False},
            },
            "required": ["address"],
        },
    },
    {
        "name": "binary_trace_asset",
        "description": "Trace a resource/asset term through exported strings and matching functions. Results are leads unless an accepted annotation confirms them.",
        "inputSchema": {"type": "object", "properties": {"term": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["term"]},
    },
    {
        "name": "binary_trace_control",
        "description": "Trace a client control name or ID through exported static evidence and function search.",
        "inputSchema": {"type": "object", "properties": {"term": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["term"]},
    },
    {
        "name": "binary_trace_packet",
        "description": "Find static packet-related candidate evidence. This does not claim a packet layout is confirmed.",
        "inputSchema": {"type": "object", "properties": {"term": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["term"]},
    },
    {
        "name": "binary_class",
        "description": "Query the conservative derived class/vtable registry. Explicit accepted evidence is required for a class-to-vtable association.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
    },
    {
        "name": "binary_review_queue",
        "description": "List non-promoting, low-confidence function-name review candidates. Proposed names are never active annotations.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}},
    },
    {
        "name": "binary_next_target",
        "description": "Return the next function to investigate from the durable work queue, skipping anything already named or recorded done/skipped. Returns {exhausted: true} when the frontier is empty. Use this to drive an autonomous, resumable loop.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "binary_propose_name",
        "description": (
            "Record a grounded function-name CANDIDATE in this agent run only. "
            "It does not change active_name or accepted annotations. Use this for unattended/local-model work."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "name": {"type": "string", "minLength": 1},
                "confidence": {"type": "string", "enum": ["medium", "high"]},
                "evidence": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                "rationale": {"type": "string", "minLength": 12},
            },
            "required": ["address", "name", "confidence", "evidence", "evidence_refs", "rationale"],
        },
    },
    {
        "name": "binary_network_map",
        "description": "Build a read-only static networking lifecycle map with API evidence, candidate functions, leads, and unresolved reconstruction contracts.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 500}}},
    },
    {
        "name": "binary_candidate_queue",
        "description": "List naming candidates in this isolated agent run; defaults to pending candidates.",
        "inputSchema": {"type": "object", "properties": {"status": {"type": "string", "enum": ["pending", "accepted", "rejected", "all"]}}},
    },
    {
        "name": "binary_review_candidate",
        "description": "Reviewer-only: accept a pending candidate into the reversible annotation overlay, or reject it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "action": {"type": "string", "enum": ["accept", "reject"]},
                "note": {"type": "string"},
            },
            "required": ["address", "action"],
        },
    },
    {
        "name": "binary_annotate",
        "description": (
            "Reviewer-only: record a confirmed, evidence-backed function name in the reversible overlay. "
            "Every evidence_ref must be grounded in this function's own imports, strings, or named relationships. "
            "Acceptance also requires a valid symbol, medium/high confidence, evidence, rationale, and either a name-linked ref "
            "or two independent refs. "
            "On success the name becomes the function's active_name and the target is marked done."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Function address or an unambiguous exact function name."},
                "name": {"type": "string", "minLength": 1, "description": "The confirmed function symbol to record."},
                "confidence": {"type": "string", "enum": ["medium", "high"]},
                "evidence": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}, "description": "Human-readable justification lines."},
                "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 3}, "description": "Concrete import, string, or named-relationship tokens grounded in this function."},
                "rationale": {"type": "string", "minLength": 12},
            },
            "required": ["address", "name", "confidence", "evidence", "evidence_refs", "rationale"],
        },
    },
    {
        "name": "binary_progress",
        "description": "Record a target outcome in the work queue (status: done | skipped | deferred) and/or return the overall progress summary. Call with no arguments for a summary only; mark 'skipped' when you cannot name a function so the loop moves on.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "status": {"type": "string", "enum": ["done", "skipped", "deferred"]},
                "note": {"type": "string"},
            },
        },
    },
]


def response(message_id, result):
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def error(message_id, code, message):
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def tool_result(value, failed=False):
    return {
        "content": [{"type": "text", "text": json.dumps(value, indent=2, ensure_ascii=False)}],
        "isError": failed,
    }


def _run_id(store):
    """Return the isolated MCP run id, including for in-process adapters."""

    return getattr(store, "agent_run_id", "overnight") or "overnight"


def _annotate_guarded(store, arguments):
    """Verify the model's cited evidence against the function, then record it.

    The evidence refs must actually appear in the function's own bundle, so a
    hallucinated justification is rejected before it becomes an accepted name.
    """
    refs = arguments.get("evidence_refs", []) or []
    lookup = store.lookup(arguments.get("address", ""), include_decompiler=True, include_assembly=True)
    # Use the canonical address the store resolved, so the verifier, the write,
    # and the ledger all key off the same address (a name and its address must
    # not desync).
    resolved = lookup.get("function", {}).get("address", arguments.get("address", ""))
    ok, missing = verify_evidence_refs(lookup, refs)
    if not ok:
        reason = (
            "no usable evidence_refs (each must be at least 3 characters)" if not missing
            else "cited evidence_refs are not import names, string values, or callee names of this function"
        )
        # Count the failed attempt so a target that never grounds is retired.
        ledger.record(store.export_path, resolved, "deferred", note=reason, run_id=_run_id(store))
        return {
            "accepted": False,
            "address": resolved,
            "reason": reason,
            "missing_refs": missing,
            "hint": "Cite concrete import names, string values, or callee names you saw in binary_lookup, or mark the target skipped.",
        }
    policy_ok, reason = validate_annotation_proposal(
        arguments.get("name", ""),
        arguments.get("confidence", ""),
        arguments.get("evidence", []) or [],
        arguments.get("rationale", ""),
        refs,
    )
    if not policy_ok:
        ledger.record(store.export_path, resolved, "deferred", note=reason, run_id=_run_id(store))
        return {
            "accepted": False,
            "address": resolved,
            "reason": reason,
            "missing_refs": [],
            "hint": "Use a valid evidence-linked symbol with medium/high confidence, evidence lines, and a concrete rationale; otherwise skip.",
        }
    result = annotate(
        store.export_path,
        resolved,
        str(arguments.get("name", "")).strip(),
        arguments.get("confidence", "medium"),
        status="accepted",
        source="autonomous-agent",
        evidence=arguments.get("evidence", []) or [],
        rationale=arguments.get("rationale", ""),
    )
    # Make the new name visible to this same session, then record progress.
    store.reload_annotations()
    ledger.record(store.export_path, result["address"], "done", note="annotated as {}".format(result["name"]), run_id=_run_id(store))
    return {"accepted": True, **result}


def _propose_guarded(store, arguments):
    refs = arguments.get("evidence_refs", []) or []
    lookup = store.lookup(arguments.get("address", ""), include_decompiler=True, include_assembly=True)
    resolved = lookup.get("function", {}).get("address", arguments.get("address", ""))
    ok, missing = verify_evidence_refs(lookup, refs)
    if not ok:
        reason = "cited evidence_refs are not grounded in this function"
        ledger.record(store.export_path, resolved, "deferred", note=reason, run_id=_run_id(store))
        return {"accepted": False, "address": resolved, "reason": reason, "missing_refs": missing}
    policy_ok, reason = validate_annotation_proposal(
        arguments.get("name", ""), arguments.get("confidence", ""),
        arguments.get("evidence", []) or [], arguments.get("rationale", ""), refs,
    )
    if not policy_ok:
        ledger.record(store.export_path, resolved, "deferred", note=reason, run_id=_run_id(store))
        return {"accepted": False, "address": resolved, "reason": reason, "missing_refs": []}
    result = naming_candidates.propose(store.export_path, _run_id(store), lookup, arguments)
    ledger.record(store.export_path, resolved, "done", note="proposed {}".format(result["proposed_name"]), run_id=_run_id(store))
    return {"accepted": True, "promoted": False, **result}


def call_tool(store, name, arguments):
    if name == "binary_status":
        return dict(store.status(), agent_run_id=_run_id(store), progress=ledger.summary(store, store.export_path, _run_id(store)))
    if name == "binary_propose_name":
        return _propose_guarded(store, arguments)
    if name == "binary_candidate_queue":
        status = arguments.get("status", "pending")
        return naming_candidates.queue(store.export_path, _run_id(store), "" if status == "all" else status)
    if name == "binary_review_candidate":
        return naming_candidates.review(store, _run_id(store), arguments.get("address", ""), arguments.get("action", ""), arguments.get("note", ""))
    if name == "binary_annotate":
        return _annotate_guarded(store, arguments)
    if name == "binary_next_target":
        target = ledger.next_target(store, store.export_path, run_id=_run_id(store))
        return target if target is not None else {"exhausted": True}
    if name == "binary_progress":
        recorded = None
        if arguments.get("address") and arguments.get("status"):
            # Canonicalize (and validate) so the ledger key matches the frontier;
            # an unknown address raises EvidenceError -> surfaced as a tool error.
            resolved = store.resolve_address(arguments["address"])
            recorded = ledger.record(store.export_path, resolved, arguments["status"], arguments.get("note", ""), run_id=_run_id(store))
        return {"recorded": recorded, "summary": ledger.summary(store, store.export_path, _run_id(store))}
    if name == "binary_search":
        return store.search(arguments.get("query", ""), arguments.get("limit", 20))
    if name == "binary_lookup":
        return store.lookup(
            arguments.get("address", ""),
            arguments.get("include_decompiler", True),
            arguments.get("include_assembly", False),
        )
    if name == "binary_trace_asset":
        return store.trace(arguments.get("term", ""), "asset", arguments.get("limit", 20))
    if name == "binary_trace_control":
        return store.trace(arguments.get("term", ""), "control", arguments.get("limit", 20))
    if name == "binary_trace_packet":
        return store.trace(arguments.get("term", ""), "packet-candidate", arguments.get("limit", 20))
    if name == "binary_network_map":
        return build_network_report(store.export_path, max(1, min(int(arguments.get("limit", 100)), 500)))
    if name == "binary_class":
        return store.class_info(arguments.get("query", ""), arguments.get("limit", 20))
    if name == "binary_review_queue":
        return store.review_queue(arguments.get("query", ""), arguments.get("limit", 20))
    raise EvidenceError("Unknown tool: {}".format(name))


def handle(store, message):
    if not isinstance(message, dict):
        return error(None, -32600, "Invalid Request: message must be a JSON object")
    method = message.get("method", "")
    message_id = message.get("id")
    params = message.get("params", {}) or {}
    if method == "initialize":
        return response(message_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })
    if method == "tools/list":
        return response(message_id, {"tools": TOOLS})
    if method == "tools/call":
        try:
            arguments = params.get("arguments", {}) or {}
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be a JSON object")
            value = call_tool(store, params.get("name", ""), arguments)
            return response(message_id, tool_result(value))
        except (EvidenceError, OSError, ValueError) as exc:
            return response(message_id, tool_result({"error": str(exc)}, True))
    if method == "ping":
        return response(message_id, {})
    if method.startswith("notifications/"):
        return None
    return error(message_id, -32601, "Unsupported method: {}".format(method))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve a Ghidra export through local evidence MCP tools.")
    parser.add_argument("--export", dest="export_path", default=DEFAULT_EXPORT_PATH)
    parser.add_argument("--run-id", default=os.environ.get("RE_EVIDENCE_AGENT_RUN", "overnight"), help="Isolated agent run under <export>/agent_runs (default: overnight).")
    args = parser.parse_args(argv)
    try:
        store = LocalEvidenceStore(args.export_path)
        store.agent_run_id = args.run_id
    except (EvidenceError, OSError, ValueError) as exc:
        print("[ERROR] {}".format(exc), file=sys.stderr)
        return 1

    for line in sys.stdin:
        try:
            message = json.loads(line)
            result = handle(store, message)
            if result is not None:
                print(json.dumps(result, ensure_ascii=False), flush=True)
        except json.JSONDecodeError as exc:
            print(json.dumps(error(None, -32700, "Invalid JSON: {}".format(exc))), flush=True)
        except Exception as exc:  # never let one malformed message kill an overnight run
            print("[WARN] skipped message: {}".format(exc), file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
