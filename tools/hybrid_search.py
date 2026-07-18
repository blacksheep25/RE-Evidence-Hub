"""Supported optional hybrid retrieval over local metadata + semantic index."""

from __future__ import annotations

import json

from tools.local_evidence import LocalEvidenceStore
from tools.semantic_index import SemanticSearch


class HybridSearch:
    def __init__(self, export_path):
        self.store = LocalEvidenceStore(export_path)
        self.semantic_backend = SemanticSearch(export_path)

    def semantic(self, query, limit=10):
        return self.semantic_backend.search(query, limit)

    def keyword(self, query, limit=10):
        return self.store.search(query, limit).get("results", [])

    def context(self, query):
        candidates = {}
        for item in self.keyword(query, 5):
            candidates[item["address"]] = {"source": "keyword", "summary": item}
        for item in self.semantic(query, 10):
            address = item["function"]["address"]
            candidates.setdefault(address, {"source": "semantic", "summary": item["function"]})
            candidates[address]["semantic_score"] = item["semantic_score"]
        output = ["===== HYBRID BINARY EVIDENCE LEADS ====="]
        for address, item in list(candidates.items())[:10]:
            summary = item["summary"]
            output.append("\n{} @ {} [{}]".format(summary.get("active_name") or summary.get("raw_name", ""), address, item["source"]))
            if "semantic_score" in item:
                output.append("semantic_score={:.4f}".format(item["semantic_score"]))
        return "\n".join(output)
