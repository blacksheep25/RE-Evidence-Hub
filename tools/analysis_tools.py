"""Legacy analysis-tool facade over the local evidence store.

Older planning scripts import AnalysisTools and expect list-shaped search
results plus methods such as get_function/search_strings.  Keep that API, but
source the data from EvidenceTools/LocalEvidenceStore so accepted annotations
and derived evidence stay consistent with the HTTP and MCP adapters.
"""

from __future__ import annotations

try:
    from tools.evidence_tools import EvidenceTools
except ImportError:
    from evidence_tools import EvidenceTools


class AnalysisTools(EvidenceTools):
    """Compatibility wrapper for older scripts."""

    def __init__(self, export_path):
        super().__init__(export_path)
        self.index = self.functions

    @staticmethod
    def _legacy_name(item):
        return item.get("active_name") or item.get("raw_name") or item.get("name") or item.get("address", "")

    def search(self, keyword, limit=50):
        result = self.store.search(keyword, limit)
        output = []
        for item in result.get("results", []):
            output.append({
                "address": item.get("address", ""),
                "name": self._legacy_name(item),
                "raw_name": item.get("raw_name", ""),
                "active_name": item.get("active_name"),
                "match_source": item.get("match_source", ""),
                "score": item.get("size") or 0,
                "annotation": item.get("annotation"),
            })
        return output

    def semantic_search(self, query, limit=10):
        result = super().semantic_search(query, limit)
        return result.get("results", []) if isinstance(result, dict) else result

    def get_function(self, address):
        try:
            return self.store.function(address)
        except Exception as exc:
            return {"error": str(exc)}

    def search_strings(self, keyword):
        try:
            return self.store.strings(keyword, 100)
        except Exception as exc:
            return {"error": str(exc)}

    def search_imports(self, keyword):
        try:
            return self.store.imports(keyword, 100)
        except Exception as exc:
            return {"error": str(exc)}

    def get_callers(self, address):
        try:
            return self.store.callers(address)
        except Exception as exc:
            return {"error": str(exc)}

    def get_callees(self, address):
        try:
            return self.store.callees(address)
        except Exception as exc:
            return {"error": str(exc)}
