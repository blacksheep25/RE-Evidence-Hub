"""Small HTTP client for the local evidence API.

Most in-repo Python code should import LocalEvidenceStore/EvidenceTools
directly.  Use this client when a script intentionally talks to the running
HTTP adapter, for example from another process or language.
"""

from __future__ import annotations

from typing import Any, Dict

import requests

try:
    from host_config import API_PORT
except ImportError:
    API_PORT = 5006


class EvidenceClient:
    def __init__(self, base_url: str | None = None, timeout: int = 30):
        self.base_url = (base_url or "http://127.0.0.1:{}".format(API_PORT)).rstrip("/")
        self.timeout = timeout

    def get(self, route: str):
        response = requests.get(self.base_url + route, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def post(self, route: str, payload: Dict[str, Any] | None = None):
        response = requests.post(self.base_url + route, json=payload or {}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def status(self):
        return self.get("/status")

    def search(self, query: str, limit: int = 20):
        return self.post("/search", {"query": query, "limit": limit})

    def lookup(
        self,
        address: str,
        include_decompiler: bool = True,
        include_assembly: bool = False,
        evidence_limit: int = 30,
    ):
        return self.post("/lookup", {
            "address": address,
            "include_decompiler": include_decompiler,
            "include_assembly": include_assembly,
            "evidence_limit": evidence_limit,
        })

    def strings(self, query: str, limit: int = 20):
        return self.post("/strings", {"query": query, "limit": limit})

    def imports(self, query: str, limit: int = 20):
        return self.post("/imports", {"query": query, "limit": limit})

    def callers(self, address: str):
        return self.post("/callers", {"address": address})

    def callees(self, address: str):
        return self.post("/callees", {"address": address})

    def asset(self, term: str, limit: int = 20):
        return self.post("/asset", {"term": term, "limit": limit})

    def control(self, term: str, limit: int = 20):
        return self.post("/control", {"term": term, "limit": limit})

    def packet(self, term: str, limit: int = 20):
        return self.post("/packet", {"term": term, "limit": limit})

    def class_info(self, query: str, limit: int = 20):
        return self.post("/class", {"query": query, "limit": limit})

    def review_queue(self, query: str = "", limit: int = 20):
        return self.post("/review", {"query": query, "limit": limit})

    def reload_annotations(self):
        return self.post("/reload")
