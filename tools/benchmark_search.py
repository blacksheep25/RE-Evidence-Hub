#!/usr/bin/env python3
"""Repeatable performance benchmark for the supported local evidence path."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from typing import Any, Callable, Dict, List

from tools.local_evidence import LocalEvidenceStore


def _measure(action: Callable[[], Any], repeats: int) -> Dict[str, float]:
    samples = []
    for _ in range(max(1, repeats)):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "min_ms": round(min(samples), 3),
        "median_ms": round(statistics.median(samples), 3),
        "max_ms": round(max(samples), 3),
    }


def benchmark(export_path: str, queries: List[str], repeats: int = 3) -> Dict[str, Any]:
    started = time.perf_counter()
    store = LocalEvidenceStore(export_path)
    init_ms = (time.perf_counter() - started) * 1000
    first_address = sorted(store.functions)[0]
    results = {
        "store_init": {"median_ms": round(init_ms, 3)},
        "lookup": _measure(lambda: store.lookup(first_address, include_decompiler=False), repeats),
        "search": {},
    }
    for query in queries:
        results["search"][query] = _measure(lambda q=query: store.search(q, 20), repeats)
    return {
        "kind": "local-evidence-performance-benchmark",
        "export_path": store.export_path,
        "function_count": len(store.functions),
        "local_fts_index": store.has_local_index,
        "repeats": max(1, repeats),
        "results": results,
        "guidance": "Compare like-for-like exports and machines. Build the FTS index before benchmarking decompiler-body queries.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark LocalEvidenceStore startup, lookup, and search latency.")
    parser.add_argument("export_path")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    result = benchmark(args.export_path, args.query or ["FUN_", "send", "packet"], args.repeats)
    if args.output:
        path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
