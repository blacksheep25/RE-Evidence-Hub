"""AI-facing tools backed by the local evidence store.

This module is the in-process adapter for agents and scripts.  It deliberately
uses the same LocalEvidenceStore core as the HTTP and MCP adapters, so local
Python workflows get accepted annotations, class/review derived
artifacts, and reload semantics without needing a Flask process or fixed port.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from tools.local_evidence import EvidenceError, LocalEvidenceStore
except ImportError:  # Support running scripts from inside the tools directory.
    from local_evidence import EvidenceError, LocalEvidenceStore

try:
    from host_config import DEFAULT_EXPORT_PATH
except ImportError:
    from project_layout import project_export_path
    DEFAULT_EXPORT_PATH = project_export_path("sample_program.exe")


class EvidenceTools:
    """Structured tool surface for local AI investigation loops."""

    def __init__(self, export_path: str):
        self.export_path = export_path
        self.store = LocalEvidenceStore(export_path)
        self.functions = self.store.functions
        self._semantic = None
        self._semantic_error = None

    def tool_definitions(self):
        return [
            {
                "name": "status",
                "description": "Return the active export identity and available derived evidence indexes.",
                "parameters": {},
            },
            {
                "name": "search",
                "description": "Search raw function metadata, accepted annotations, and optional FTS body text.",
                "parameters": {"query": "string", "limit": "integer"},
            },
            {
                "name": "lookup",
                "description": "Return one evidence bundle with annotation, strings/imports, callers/callees, and decompiler data.",
                "parameters": {
                    "address": "string",
                    "include_decompiler": "boolean",
                    "include_assembly": "boolean",
                    "evidence_limit": "integer",
                },
            },
            {
                "name": "strings",
                "description": "Search exported strings and decorate referencing functions with accepted annotations.",
                "parameters": {"query": "string", "limit": "integer"},
            },
            {
                "name": "imports",
                "description": "Search imported APIs and decorate referencing functions with accepted annotations.",
                "parameters": {"query": "string", "limit": "integer"},
            },
            {
                "name": "callers",
                "description": "Return direct callers for an address or exact function name.",
                "parameters": {"address": "string"},
            },
            {
                "name": "callees",
                "description": "Return direct callees for an address or exact function name.",
                "parameters": {"address": "string"},
            },
            {
                "name": "asset",
                "description": "Trace a resource/asset term through exported strings and matching functions.",
                "parameters": {"term": "string", "limit": "integer"},
            },
            {
                "name": "control",
                "description": "Trace a UI/control-like name or ID through static evidence.",
                "parameters": {"term": "string", "limit": "integer"},
            },
            {
                "name": "packet",
                "description": "Find static packet-related candidate evidence. Results are leads, not protocol claims.",
                "parameters": {"term": "string", "limit": "integer"},
            },
            {
                "name": "class",
                "description": "Query the conservative class/vtable registry.",
                "parameters": {"query": "string", "limit": "integer"},
            },
            {
                "name": "review",
                "description": "Query non-promoting function-name review candidates.",
                "parameters": {"query": "string", "limit": "integer"},
            },
            {
                "name": "reload",
                "description": "Reload accepted annotations only; raw export data still requires service/script restart.",
                "parameters": {},
            },
            {
                "name": "semantic",
                "description": "Optional semantic search leads. Treat results as hints, not accepted evidence.",
                "parameters": {"query": "string", "limit": "integer"},
            },
        ]

    @staticmethod
    def _first(arguments: Dict[str, Any], *names: str, default: Any = "") -> Any:
        for name in names:
            value = arguments.get(name)
            if value is not None and value != "":
                return value
        return default

    def execute_tool(self, name: str, arguments: Dict[str, Any] | None = None) -> Any:
        args = arguments or {}
        try:
            if name == "status":
                return self.status()
            if name == "search":
                return self.search(self._first(args, "query", "keyword"), args.get("limit", 20))
            if name in ("lookup", "function"):
                return self.lookup(
                    self._first(args, "address", "name", "identifier"),
                    args.get("include_decompiler", True),
                    args.get("include_assembly", False),
                    args.get("evidence_limit", 30),
                )
            if name == "strings":
                return self.strings(self._first(args, "query", "keyword"), args.get("limit", 20))
            if name == "imports":
                return self.imports(self._first(args, "query", "keyword"), args.get("limit", 20))
            if name == "callers":
                return self.callers(self._first(args, "address", "name", "identifier"))
            if name == "callees":
                return self.callees(self._first(args, "address", "name", "identifier"))
            if name == "asset":
                return self.asset(self._first(args, "term", "query", "keyword"), args.get("limit", 20))
            if name == "control":
                return self.control(self._first(args, "term", "query", "keyword"), args.get("limit", 20))
            if name == "packet":
                return self.packet(self._first(args, "term", "query", "keyword"), args.get("limit", 20))
            if name == "class":
                return self.class_info(self._first(args, "query", "name", "class"), args.get("limit", 20))
            if name == "review":
                return self.review_queue(self._first(args, "query", "keyword"), args.get("limit", 20))
            if name == "reload":
                return self.reload_annotations()
            if name == "semantic":
                return self.semantic_search(self._first(args, "query", "keyword"), args.get("limit", 10))
            return {"error": "Unknown tool: {}".format(name)}
        except (EvidenceError, OSError, ValueError) as exc:
            return {"error": str(exc), "tool": name}

    def status(self):
        return self.store.status()

    def search(self, query: str, limit: Any = 20):
        return self.store.search(query, limit)

    def lookup(
        self,
        identifier: str,
        include_decompiler: bool = True,
        include_assembly: bool = False,
        evidence_limit: Any = 30,
    ):
        return self.store.lookup(identifier, include_decompiler, include_assembly, evidence_limit)

    def function(self, identifier: str):
        return self.store.function(identifier)

    def strings(self, query: str, limit: Any = 20):
        return self.store.strings(query, limit)

    def imports(self, query: str, limit: Any = 20):
        return self.store.imports(query, limit)

    def callers(self, identifier: str):
        return self.store.callers(identifier)

    def callees(self, identifier: str):
        return self.store.callees(identifier)

    def asset(self, term: str, limit: Any = 20):
        return self.store.trace(term, "asset", limit)

    def control(self, term: str, limit: Any = 20):
        return self.store.trace(term, "control", limit)

    def packet(self, term: str, limit: Any = 20):
        return self.store.trace(term, "packet-candidate", limit)

    def class_info(self, query: str, limit: Any = 20):
        return self.store.class_info(query, limit)

    def review_queue(self, query: str = "", limit: Any = 20):
        return self.store.review_queue(query, limit)

    def reload_annotations(self):
        return self.store.reload_annotations()

    def semantic_search(self, query: str, limit: Any = 10):
        if self._semantic_error:
            return {"query": query, "available": False, "error": self._semantic_error, "results": []}
        try:
            if self._semantic is None:
                try:
                    from tools.hybrid_search import HybridSearch
                except ImportError:
                    from hybrid_search import HybridSearch
                self._semantic = HybridSearch(self.export_path)
            return {
                "query": query,
                "available": True,
                "mode": "optional-semantic",
                "results": self._semantic.semantic(query, limit),
            }
        except Exception as exc:
            self._semantic_error = str(exc)
            return {"query": query, "available": False, "error": self._semantic_error, "results": []}

    # Legacy names used by older planning scripts.
    def get_function(self, address: str):
        return self.function(address)

    def search_strings(self, keyword: str):
        return self.strings(keyword)

    def search_imports(self, keyword: str):
        return self.imports(keyword)

    def get_callers(self, address: str):
        return self.callers(address)

    def get_callees(self, address: str):
        return self.callees(address)


def _print_json(value: Any, compact: bool = False) -> None:
    if compact:
        print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(value, indent=2, ensure_ascii=False))


def _add_query_command(subparsers, name: str, help_text: str, parents=None):
    command = subparsers.add_parser(name, help=help_text, parents=parents or [])
    command.add_argument("query", nargs="?", default="")
    command.add_argument("--limit", type=int, default=20)
    return command


def build_parser():
    parser = argparse.ArgumentParser(
        description="Query a Ghidra AI export through the in-process local evidence tools."
    )
    parser.add_argument(
        "--export",
        dest="export_path",
        default=DEFAULT_EXPORT_PATH,
        help="Export folder to query. Defaults to GHIDRA_AI_EXPORT_PATH or host_config.DEFAULT_EXPORT_PATH.",
    )
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    compact_parent = argparse.ArgumentParser(add_help=False)
    compact_parent.add_argument("--compact", action="store_true", default=argparse.SUPPRESS, help="Print compact JSON.")
    command_parents = [compact_parent]

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Show export identity and available derived evidence.", parents=command_parents)
    subparsers.add_parser("tools", help="List available evidence tool definitions.", parents=command_parents)

    _add_query_command(subparsers, "search", "Search functions by metadata, accepted annotation, or FTS body text.", command_parents)
    _add_query_command(subparsers, "strings", "Search exported strings.", command_parents)
    _add_query_command(subparsers, "imports", "Search imported APIs.", command_parents)
    _add_query_command(subparsers, "asset", "Trace an asset/resource term.", command_parents)
    _add_query_command(subparsers, "control", "Trace a UI/control-like term.", command_parents)
    _add_query_command(subparsers, "packet", "Trace packet-related evidence leads.", command_parents)
    _add_query_command(subparsers, "class", "Query the class/vtable registry.", command_parents)
    _add_query_command(subparsers, "review", "Query the non-promoting name review queue.", command_parents)
    _add_query_command(subparsers, "semantic", "Run optional semantic search leads.", command_parents)

    lookup = subparsers.add_parser("lookup", help="Inspect one function evidence bundle.", parents=command_parents)
    lookup.add_argument("address", help="Function address or exact accepted/raw name.")
    lookup.add_argument("--no-decompiler", action="store_true", help="Omit decompiler output.")
    lookup.add_argument("--assembly", action="store_true", help="Include assembly output.")
    lookup.add_argument("--evidence-limit", type=int, default=30)

    function = subparsers.add_parser("function", help="Return the raw function document plus annotation summary.", parents=command_parents)
    function.add_argument("address", help="Function address or exact accepted/raw name.")

    callers = subparsers.add_parser("callers", help="List direct callers.", parents=command_parents)
    callers.add_argument("address", help="Function address or exact accepted/raw name.")

    callees = subparsers.add_parser("callees", help="List direct callees.", parents=command_parents)
    callees.add_argument("address", help="Function address or exact accepted/raw name.")

    subparsers.add_parser("reload", help="Reload accepted annotations only.", parents=command_parents)
    return parser


def run_command(args):
    tools = EvidenceTools(args.export_path)
    command = args.command
    if command == "status":
        return tools.status()
    if command == "tools":
        return {"tools": tools.tool_definitions()}
    if command == "lookup":
        return tools.lookup(
            args.address,
            include_decompiler=not args.no_decompiler,
            include_assembly=args.assembly,
            evidence_limit=args.evidence_limit,
        )
    if command == "function":
        return tools.function(args.address)
    if command == "callers":
        return tools.callers(args.address)
    if command == "callees":
        return tools.callees(args.address)
    if command == "reload":
        return tools.reload_annotations()
    if command in ("search", "strings", "imports", "asset", "control", "packet", "class", "review", "semantic"):
        return tools.execute_tool(command, {"query": args.query, "term": args.query, "limit": args.limit})
    raise EvidenceError("Unknown command: {}".format(command))


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        _print_json(run_command(args), args.compact)
        return 0
    except (EvidenceError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("[ERROR] {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
