#!/usr/bin/env python3
"""Portable per-export semantic index using sentence-transformers + NumPy."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import tempfile
from typing import Any, Dict, List

import numpy as np

from host_config import EMBEDDING_MODEL
from tools.local_evidence import LocalEvidenceStore
from tools.file_lock import locked_file


INDEX_DIR = os.path.join("derived", "semantic")
METADATA_NAME = "metadata.json"
VECTORS_NAME = "vectors.npz"
SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def index_paths(export_path: str):
    directory = os.path.join(os.path.abspath(export_path), INDEX_DIR)
    return directory, os.path.join(directory, METADATA_NAME), os.path.join(directory, VECTORS_NAME)


def _function_text(raw: Dict[str, Any], max_chars: int) -> str:
    decompiler = raw.get("decompiler", {})
    code = decompiler.get("c_code", "") if isinstance(decompiler, dict) else ""
    values = [
        raw.get("name", ""), raw.get("namespace", ""), raw.get("signature", ""),
        " ".join(str(item.get("name", "")) for item in raw.get("calls", []) if isinstance(item, dict)),
        str(code)[:max_chars],
    ]
    return "\n".join(str(value) for value in values if value)


def build_index(export_path: str, model_name: str = EMBEDDING_MODEL,
                batch_size: int = 32, max_chars: int = 8000) -> Dict[str, Any]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install the semantic extra: pip install -e .[semantic]") from exc
    store = LocalEvidenceStore(export_path)
    addresses: List[str] = []
    texts: List[str] = []
    fingerprint = hashlib.sha256()
    for address in sorted(store.functions):
        raw = store.function(address)
        addresses.append(address)
        texts.append(_function_text(raw, max_chars))
        fingerprint.update((address + "\0" + str(raw.get("hash", "")) + "\n").encode("utf-8"))
    model = SentenceTransformer(model_name)
    vectors = model.encode(texts, batch_size=max(1, batch_size), normalize_embeddings=True, show_progress_bar=True)
    vectors = np.asarray(vectors, dtype=np.float32)
    directory, metadata_path, vectors_path = index_paths(store.export_path)
    os.makedirs(directory, exist_ok=True)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "kind": "portable-function-semantic-index",
        "generated_utc": _utc_now(),
        "model": model_name,
        "function_count": len(addresses),
        "source_fingerprint_sha256": fingerprint.hexdigest(),
        "addresses": addresses,
    }
    with locked_file(metadata_path):
        meta_handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=".semantic-", suffix=".json.tmp", delete=False)
        vector_handle = tempfile.NamedTemporaryFile("wb", dir=directory, prefix=".semantic-", suffix=".npz", delete=False)
        vector_handle.close()
        try:
            json.dump(metadata, meta_handle, indent=2, sort_keys=True)
            meta_handle.flush()
            os.fsync(meta_handle.fileno())
            meta_handle.close()
            np.savez_compressed(vector_handle.name, vectors=vectors)
            os.replace(vector_handle.name, vectors_path)
            os.replace(meta_handle.name, metadata_path)
        finally:
            for path in (meta_handle.name, vector_handle.name):
                if os.path.exists(path):
                    os.remove(path)
    return {"metadata": metadata_path, "vectors": vectors_path, "function_count": len(addresses), "model": model_name}


class SemanticSearch:
    def __init__(self, export_path: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install the semantic extra: pip install -e .[semantic]") from exc
        self.store = LocalEvidenceStore(export_path)
        _directory, metadata_path, vectors_path = index_paths(self.store.export_path)
        if not os.path.isfile(metadata_path) or not os.path.isfile(vectors_path):
            raise RuntimeError("Semantic index is absent; run `revhub semantic-index` first")
        with open(metadata_path, encoding="utf-8", errors="replace") as handle:
            self.metadata = json.load(handle)
        if self.metadata.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError("Unsupported semantic index schema; rebuild it")
        self.addresses = self.metadata.get("addresses", [])
        with np.load(vectors_path) as bundle:
            self.vectors = np.asarray(bundle["vectors"], dtype=np.float32)
        if len(self.addresses) != len(self.vectors):
            raise RuntimeError("Semantic metadata/vector count mismatch; rebuild it")
        self.model = SentenceTransformer(self.metadata["model"])

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        term = str(query or "").strip()
        if not term:
            raise ValueError("A non-empty semantic query is required")
        vector = np.asarray(self.model.encode([term], normalize_embeddings=True)[0], dtype=np.float32)
        scores = self.vectors @ vector
        maximum = max(1, min(int(limit), 100, len(scores)))
        indices = np.argpartition(-scores, maximum - 1)[:maximum]
        indices = indices[np.argsort(-scores[indices])]
        return [
            dict(self.store.lookup(self.addresses[index], include_decompiler=False), semantic_score=float(scores[index]))
            for index in indices
        ]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the one supported portable semantic index for an export.")
    parser.add_argument("export_path")
    parser.add_argument("--model", default=EMBEDDING_MODEL)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-chars", type=int, default=8000)
    args = parser.parse_args(argv)
    print(json.dumps(build_index(args.export_path, args.model, args.batch_size, args.max_chars), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
