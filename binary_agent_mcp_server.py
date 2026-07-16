"""Dependency-free stdio MCP adapter for the local evidence store.

Run this process from an MCP-capable client.  It deliberately exposes only
read-only, export-backed tools; it never writes to the Ghidra database or raw
export files.
"""

from __future__ import annotations

import argparse
import json
import sys

from host_config import DEFAULT_EXPORT_PATH
from tools.local_evidence import EvidenceError, LocalEvidenceStore


SERVER_INFO = {"name": "binary-local-evidence", "version": "1.0.0"}

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


def call_tool(store, name, arguments):
    if name == "binary_status":
        return store.status()
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
    if name == "binary_class":
        return store.class_info(arguments.get("query", ""), arguments.get("limit", 20))
    if name == "binary_review_queue":
        return store.review_queue(arguments.get("query", ""), arguments.get("limit", 20))
    raise EvidenceError("Unknown tool: {}".format(name))


def handle(store, message):
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
            value = call_tool(store, params.get("name", ""), params.get("arguments", {}) or {})
            return response(message_id, tool_result(value))
        except (EvidenceError, OSError, ValueError) as exc:
            return response(message_id, tool_result({"error": str(exc)}, True))
    if method == "ping":
        return response(message_id, {})
    if method.startswith("notifications/"):
        return None
    return error(message_id, -32601, "Unsupported method: {}".format(method))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve a Ghidra export through read-only local MCP tools.")
    parser.add_argument("--export", dest="export_path", default=DEFAULT_EXPORT_PATH)
    args = parser.parse_args(argv)
    try:
        store = LocalEvidenceStore(args.export_path)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
