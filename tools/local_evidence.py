"""Read-only, evidence-backed queries over one Ghidra AI export.

The raw Ghidra export remains immutable.  Names and conclusions come only
from the optional address-keyed annotation overlay, whose decisions retain
their evidence and confidence.  This module intentionally has no Flask,
embedding, Chroma, or LLM dependency so it can be the reliable local-first
core for both the HTTP and MCP adapters.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sqlite3
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

ANNOTATION_PATH = os.path.join("annotations", "function_names.json")
LOCAL_INDEX_NAME = "local_evidence.sqlite3"
CLASS_REGISTRY_NAME = "class_registry.json"
REVIEW_QUEUE_NAME = "name_review_queue.json"
MAX_LIMIT = 100


class EvidenceError(ValueError):
    """A caller supplied an invalid or ambiguous local-evidence request."""


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def _limit(value: Any, default: int = 20) -> int:
    try:
        return max(1, min(int(value), MAX_LIMIT))
    except (TypeError, ValueError):
        return default


def _unique_references(values: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for value in values:
        address = value.get("address", "") if isinstance(value, dict) else ""
        key = (address, value.get("name", "") if isinstance(value, dict) else "")
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


class LocalEvidenceStore:
    """Fast, read-only access to a single portable Ghidra export."""

    def __init__(self, export_path: str):
        self.export_path = os.path.abspath(export_path)
        self.manifest = self._require_json("manifest.json")
        self.index = self._require_json("index.json")
        self.functions = self.index.get("functions", {})
        if not self.functions:
            raise EvidenceError("index.json does not contain any functions")

        self._address_lookup = {address.lower(): address for address in self.functions}
        self._raw_names = {
            str(name).lower(): list(addresses)
            for name, addresses in self.index.get("function_names", {}).items()
        }
        self._strings: Optional[List[Dict[str, Any]]] = None
        self._imports: Optional[List[Dict[str, Any]]] = None
        self._strings_by_function: Optional[Dict[str, List[Dict[str, Any]]]] = None
        self._imports_by_function: Optional[Dict[str, List[Dict[str, Any]]]] = None
        self.annotations = self._load_annotations()
        self._active_names = self._build_active_name_index()
        self._local_index_path = os.path.join(self.export_path, LOCAL_INDEX_NAME)
        self._class_registry: Optional[Dict[str, Any]] = None
        self._class_registry_loaded = False
        self._review_queue: Optional[Dict[str, Any]] = None
        self._review_queue_loaded = False

    def _require_json(self, relative_path: str) -> Any:
        path = os.path.join(self.export_path, relative_path)
        if not os.path.isfile(path):
            raise EvidenceError("Export is missing {}: {}".format(relative_path, path))
        return _load_json(path)

    def _load_annotations(self) -> Dict[str, Any]:
        path = os.path.join(self.export_path, ANNOTATION_PATH)
        if not os.path.isfile(path):
            return {"entries": {}}
        data = _load_json(path)
        if data.get("kind") != "ghidra-function-name-overlay":
            raise EvidenceError("Unsupported annotation overlay: {}".format(path))
        return data

    def _build_active_name_index(self) -> Dict[str, List[str]]:
        names: Dict[str, List[str]] = defaultdict(list)
        for address, entry in self.annotations.get("entries", {}).items():
            name = entry.get("active_name", "")
            if name:
                names[name.lower()].append(address)
        return names

    def reload_annotations(self) -> Dict[str, Any]:
        """Reload only the reversible name overlay, never the raw export."""
        self.annotations = self._load_annotations()
        self._active_names = self._build_active_name_index()
        return {
            "accepted_annotation_count": len(self._active_names),
            "annotation_path": os.path.join(self.export_path, ANNOTATION_PATH),
        }

    @property
    def has_local_index(self) -> bool:
        return os.path.isfile(self._local_index_path)

    def _derived_json(self, name: str, loaded_flag: str, value_flag: str) -> Optional[Dict[str, Any]]:
        """Load an optional immutable-derived artifact once, without guessing it."""
        if not getattr(self, loaded_flag):
            path = os.path.join(self.export_path, name)
            value = _load_json(path) if os.path.isfile(path) else None
            setattr(self, value_flag, value if isinstance(value, dict) else None)
            setattr(self, loaded_flag, True)
        return getattr(self, value_flag)

    def _classes(self) -> Optional[Dict[str, Any]]:
        return self._derived_json(CLASS_REGISTRY_NAME, "_class_registry_loaded", "_class_registry")

    def _review(self) -> Optional[Dict[str, Any]]:
        return self._derived_json(REVIEW_QUEUE_NAME, "_review_queue_loaded", "_review_queue")

    def status(self) -> Dict[str, Any]:
        binary = self.manifest.get("binary", {})
        return {
            "mode": "local-export",
            "export_path": self.export_path,
            "binary": {
                "name": binary.get("name", ""),
                "image_base": binary.get("image_base", ""),
                "language": self.manifest.get("language", {}).get("id", ""),
            },
            "function_count": len(self.functions),
            "accepted_annotation_count": len(self._active_names),
            "local_fts_index": self.has_local_index,
            "semantic_search": "optional; not loaded by the local evidence service",
            "class_registry": self._derived_status(self._classes(), "class_count"),
            "name_review_queue": self._derived_status(self._review(), "candidate_count"),
        }

    @staticmethod
    def _derived_status(value: Optional[Dict[str, Any]], count_key: str) -> Dict[str, Any]:
        if not value:
            return {"available": False}
        return {
            "available": True,
            "generated_utc": value.get("generated_utc", ""),
            count_key: value.get("summary", {}).get(count_key, 0),
        }

    def _annotation(self, address: str, raw_function: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        entry = self.annotations.get("entries", {}).get(address)
        if not entry or not entry.get("active_name"):
            return None

        active_name = entry["active_name"]
        decision = next(
            (
                item
                for item in reversed(entry.get("decisions", []))
                if item.get("name") == active_name and item.get("status") == "accepted"
            ),
            None,
        )
        if decision is None:
            return {
                "active_name": active_name,
                "status": "unresolved-overlay-state",
                "confidence": "",
                "evidence": [],
                "rationale": "",
                "source": "",
                "stale": None,
            }

        stale = None
        if raw_function is not None:
            saved_hash = decision.get("function_identity", {}).get("assembly_sha256")
            current_hash = raw_function.get("hash")
            stale = bool(saved_hash and current_hash and saved_hash != current_hash)

        return {
            "active_name": active_name,
            "status": decision.get("status", ""),
            "confidence": decision.get("confidence", ""),
            "evidence": decision.get("evidence", []),
            "rationale": decision.get("rationale", ""),
            "source": decision.get("source", ""),
            "created_utc": decision.get("created_utc", ""),
            "stale": stale,
        }

    def resolve_address(self, identifier: str) -> str:
        requested = str(identifier or "").strip()
        if not requested:
            raise EvidenceError("A function address or exact function name is required")

        address = self._address_lookup.get(requested.lower())
        if address:
            return address

        candidates = list(self._active_names.get(requested.lower(), []))
        candidates.extend(self._raw_names.get(requested.lower(), []))
        candidates = sorted(set(candidates))
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise EvidenceError("Function name is ambiguous; use an address: {}".format(", ".join(candidates[:10])))
        raise EvidenceError("Function was not found: {}".format(requested))

    def _load_function(self, address: str) -> Dict[str, Any]:
        entry = self.functions.get(address)
        if not entry:
            raise EvidenceError("Function was not found: {}".format(address))
        path = os.path.join(self.export_path, entry.get("file", "functions/{}.json".format(address)))
        if not os.path.isfile(path):
            raise EvidenceError("Function record is missing: {}".format(path))
        return _load_json(path)

    def _function_summary(self, address: str, raw_function: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        record = raw_function or self.functions.get(address, {})
        annotation = self._annotation(address, raw_function)
        return {
            "address": address,
            "raw_name": record.get("name", ""),
            "active_name": annotation.get("active_name") if annotation else None,
            "namespace": record.get("namespace", ""),
            "signature": record.get("signature", ""),
            "size": record.get("size"),
            "hash": record.get("hash", "") if raw_function else "",
            "annotation": annotation,
        }

    def _decorate_reference(self, reference: Dict[str, Any]) -> Dict[str, Any]:
        value = copy.deepcopy(reference)
        address = value.get("address", "")
        if address in self.functions:
            summary = self._function_summary(address)
            value["raw_name"] = summary["raw_name"]
            value["active_name"] = summary["active_name"]
            value["name"] = summary["active_name"] or summary["raw_name"]
        return value

    def _load_evidence_indexes(self) -> None:
        if self._strings_by_function is not None:
            return

        self._strings = []
        self._imports = []
        self._strings_by_function = defaultdict(list)
        self._imports_by_function = defaultdict(list)

        strings_path = os.path.join(self.export_path, "strings.json")
        if os.path.isfile(strings_path):
            raw_strings = _load_json(strings_path)
            if isinstance(raw_strings, list):
                self._strings = raw_strings
                for item in raw_strings:
                    compact = {"address": item.get("address", ""), "value": item.get("value", "")}
                    for function in item.get("functions", []):
                        address = function.get("address", "")
                        if address:
                            self._strings_by_function[address].append(compact)

        imports_path = os.path.join(self.export_path, "imports.json")
        if os.path.isfile(imports_path):
            raw_imports = _load_json(imports_path)
            if isinstance(raw_imports, dict):
                raw_imports = list(raw_imports.values())
            if isinstance(raw_imports, list):
                self._imports = raw_imports
                for item in raw_imports:
                    compact = {
                        "address": item.get("address", ""),
                        "name": item.get("name", ""),
                        "library": item.get("library", ""),
                    }
                    for reference in item.get("references", []):
                        address = reference.get("address", "")
                        if address:
                            self._imports_by_function[address].append(compact)

    def function(self, identifier: str) -> Dict[str, Any]:
        address = self.resolve_address(identifier)
        raw = self._load_function(address)
        result = copy.deepcopy(raw)
        result["analysis"] = self._function_summary(address, raw)
        return result

    def callers(self, identifier: str) -> List[Dict[str, Any]]:
        raw = self._load_function(self.resolve_address(identifier))
        return [self._decorate_reference(value) for value in raw.get("called_by", []) if isinstance(value, dict)]

    def callees(self, identifier: str) -> List[Dict[str, Any]]:
        raw = self._load_function(self.resolve_address(identifier))
        return [self._decorate_reference(value) for value in raw.get("calls", []) if isinstance(value, dict)]

    def lookup(
        self,
        identifier: str,
        include_decompiler: bool = True,
        include_assembly: bool = False,
        evidence_limit: int = 30,
    ) -> Dict[str, Any]:
        address = self.resolve_address(identifier)
        raw = self._load_function(address)
        self._load_evidence_indexes()
        assert self._strings_by_function is not None
        assert self._imports_by_function is not None

        function = self._function_summary(address, raw)
        function["range"] = raw.get("range", {})
        function["instruction_count"] = raw.get("instruction_count")
        function["parameters"] = raw.get("parameters", [])
        result = {
            "target": self.status()["binary"],
            "function": function,
            "evidence": {
                "strings": self._strings_by_function.get(address, [])[:_limit(evidence_limit, 30)],
                "imports": self._imports_by_function.get(address, [])[:_limit(evidence_limit, 30)],
                "comments": raw.get("comments", [])[:_limit(evidence_limit, 30)],
                "xrefs": raw.get("xrefs", [])[:_limit(evidence_limit, 30)],
            },
            "relationships": {
                "callers": self.callers(address),
                "callees": self.callees(address),
            },
        }
        if include_decompiler:
            result["decompiler"] = raw.get("decompiler", {})
        if include_assembly:
            result["assembly"] = raw.get("assembly", "")
        return result

    def _fts_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        if not self.has_local_index:
            return []
        tokens = re.findall(r"[A-Za-z0-9_]+", query)
        if not tokens:
            return []
        expression = " OR ".join('"{}"'.format(token.replace('"', '')) for token in tokens)
        connection = sqlite3.connect(self._local_index_path)
        try:
            rows = connection.execute(
                "SELECT address, bm25(function_fts) AS rank FROM function_fts WHERE function_fts MATCH ? ORDER BY rank LIMIT ?",
                (expression, limit),
            ).fetchall()
        finally:
            # sqlite3's context manager commits/rolls back but does not close
            # the handle. Closing matters on Windows so a rebuilt derived
            # index can be replaced or a temporary fixture can be removed.
            connection.close()
        return [
            {"address": address, "source": "function-body", "rank": rank}
            for address, rank in rows
            if address in self.functions
        ]

    def search(self, query: str, limit: Any = 20) -> Dict[str, Any]:
        term = str(query or "").strip()
        if not term:
            raise EvidenceError("A non-empty search query is required")
        maximum = _limit(limit)
        lowered = term.lower()
        matches: Dict[str, Dict[str, Any]] = {}

        for address, entry in self.functions.items():
            raw_name = entry.get("name", "")
            namespace = entry.get("namespace", "")
            if lowered in raw_name.lower() or lowered in namespace.lower() or lowered in address.lower():
                matches[address] = {"address": address, "source": "function-metadata"}

        for name, addresses in self._active_names.items():
            if lowered in name:
                for address in addresses:
                    matches[address] = {"address": address, "source": "accepted-annotation"}

        for item in self._fts_search(term, maximum):
            matches.setdefault(item["address"], item)

        ordered = list(matches.values())
        ordered.sort(key=lambda item: (item["source"] != "accepted-annotation", item["source"] != "function-metadata", item["address"]))
        return {
            "query": term,
            "local_fts_index": self.has_local_index,
            "results": [
                dict(self._function_summary(item["address"]), match_source=item["source"])
                for item in ordered[:maximum]
            ],
        }

    def strings(self, query: str, limit: Any = 20) -> List[Dict[str, Any]]:
        term = str(query or "").strip().lower()
        if not term:
            raise EvidenceError("A non-empty string query is required")
        self._load_evidence_indexes()
        assert self._strings is not None
        output = []
        for item in self._strings:
            if term not in str(item.get("value", "")).lower():
                continue
            value = {
                "address": item.get("address", ""),
                "value": item.get("value", ""),
                "functions": [self._decorate_reference(reference) for reference in item.get("functions", [])],
            }
            output.append(value)
            if len(output) >= _limit(limit):
                break
        return output

    def imports(self, query: str, limit: Any = 20) -> List[Dict[str, Any]]:
        term = str(query or "").strip().lower()
        if not term:
            raise EvidenceError("A non-empty import query is required")
        self._load_evidence_indexes()
        assert self._imports is not None
        output = []
        for item in self._imports:
            if term not in ("{} {}".format(item.get("name", ""), item.get("library", "")).lower()):
                continue
            value = {
                "address": item.get("address", ""),
                "name": item.get("name", ""),
                "library": item.get("library", ""),
                "references": [self._decorate_reference(reference) for reference in item.get("references", [])],
            }
            output.append(value)
            if len(output) >= _limit(limit):
                break
        return output

    def class_info(self, query: str, limit: Any = 20) -> Dict[str, Any]:
        term = str(query or "").strip()
        if not term:
            raise EvidenceError("A non-empty class query is required")
        registry = self._classes()
        if not registry:
            return {
                "query": term,
                "available": False,
                "hint": "Run tools/build_class_registry.py <export> and restart the HTTP/MCP service.",
                "classes": [],
            }
        lowered = term.lower()
        classes = registry.get("classes", [])
        # Registry schema v1 initially used a mapping. Accept that old derived
        # form too so an existing export remains queryable until rebuilt.
        if isinstance(classes, dict):
            classes = [{"name": name, **value} for name, value in classes.items()]
        matched = [
            value for value in classes
            if lowered in str(value.get("name", "")).lower()
            or any(lowered in str(alias).lower() for alias in value.get("aliases", []))
        ]
        matched.sort(key=lambda value: (
            str(value.get("name", "")).lower() != lowered,
            str(value.get("name", "")).lower(),
        ))
        maximum = _limit(limit)
        return {
            "query": term,
            "available": True,
            "rules": registry.get("rules", {}),
            "classes": copy.deepcopy(matched[:maximum]),
        }

    def review_queue(self, query: str = "", limit: Any = 20) -> Dict[str, Any]:
        queue = self._review()
        term = str(query or "").strip().lower()
        if not queue:
            return {
                "query": query,
                "available": False,
                "hint": "Run tools/build_name_review_queue.py <export> and restart the HTTP/MCP service.",
                "candidates": [],
            }
        candidates = queue.get("candidates", [])
        if term:
            candidates = [
                item for item in candidates
                if term in " ".join(str(item.get(key, "")) for key in ("address", "raw_name", "kind", "proposed_name")).lower()
                or term in json.dumps(item.get("evidence", []), ensure_ascii=False).lower()
            ]
        maximum = _limit(limit)
        return {
            "query": query,
            "available": True,
            "rules": queue.get("rules", {}),
            "summary": queue.get("summary", {}),
            "candidates": copy.deepcopy(candidates[:maximum]),
        }

    def trace(self, term: str, kind: str = "term", limit: Any = 20) -> Dict[str, Any]:
        """Return evidence links for a named asset, control, packet term, or plain term.

        Packet/control labels describe the question type only; this method does
        not claim that every hit has been protocol or class validated.
        """
        maximum = _limit(limit)
        string_hits = self.strings(term, maximum)
        function_hits = self.search(term, maximum).get("results", [])
        from_strings = []
        for item in string_hits:
            from_strings.extend(item.get("functions", []))
        from_strings = _unique_references(from_strings)
        result = {
            "kind": kind,
            "term": term,
            "confidence_rule": "Results are static evidence leads. Only accepted annotations establish an active semantic name.",
            "strings": string_hits,
            "functions_referencing_strings": from_strings[:maximum],
            "function_search": function_hits[:maximum],
        }
        return result
