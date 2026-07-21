"""Compare two Ghidra exports without promoting similarity into a conclusion.

The report is a rebuildable derived artifact. Exact assembly-hash matches are
reported separately from structural leads based on shared imports, strings, and
function shape. Neither establishes shared source or equivalent behaviour.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import tempfile
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.file_lock import locked_file
from tools.local_evidence import EvidenceError, LocalEvidenceStore


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_optional_json(path):
    return _read_json(path) if os.path.isfile(path) else []


def _write_json(path, value):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=directory,
        prefix=".comparison-", suffix=".json.tmp", delete=False,
    )
    try:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(handle.name, path)
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "export"


def _function_records(store):
    index = store.index.get("functions", {})
    imports_by_function = defaultdict(set)
    strings_by_function = defaultdict(set)

    for item in _read_optional_json(os.path.join(store.export_path, "imports.json")):
        library = str(item.get("library", "")).strip()
        name = str(item.get("name", "")).strip()
        if not (library or name):
            continue
        label = "{}!{}".format(library, name).lower()
        for reference in item.get("references", []) or []:
            if reference.get("address"):
                imports_by_function[reference["address"]].add(label)
    for item in _read_optional_json(os.path.join(store.export_path, "strings.json")):
        value = str(item.get("value", "")).strip().lower()
        if not value:
            continue
        for function in item.get("functions", []) or []:
            if function.get("address"):
                strings_by_function[function["address"]].add(value)

    records = {}
    for address, meta in index.items():
        relative_path = meta.get("file", "functions/{}.json".format(address))
        raw = _read_json(os.path.join(store.export_path, relative_path))
        records[address] = {
            "address": address,
            "raw_name": raw.get("name", ""),
            "active_name": (store.annotations.get("entries", {}).get(address, {}) or {}).get("active_name"),
            "assembly_sha256": raw.get("hash", ""),
            "size": int(raw.get("size") or 0),
            "instruction_count": int(raw.get("instruction_count") or 0),
            "caller_count": len(raw.get("called_by", []) or []),
            "callee_count": len(raw.get("calls", []) or []),
            "imports": sorted(imports_by_function[address]),
            "strings": sorted(strings_by_function[address]),
        }
    return records


def _jaccard(left, right):
    left, right = set(left), set(right)
    union = left | right
    return float(len(left & right)) / len(union) if union else 0.0


def _ratio(left, right):
    left, right = int(left or 0), int(right or 0)
    return 1.0 if left == right else 1.0 - (float(abs(left - right)) / max(left, right, 1))


def _shape_similarity(left, right):
    return round((
        _ratio(left["size"], right["size"])
        + _ratio(left["instruction_count"], right["instruction_count"])
        + _ratio(left["caller_count"], right["caller_count"])
        + _ratio(left["callee_count"], right["callee_count"])
    ) / 4.0, 4)


def _summary(record):
    return {
        key: record.get(key)
        for key in ("address", "raw_name", "active_name", "assembly_sha256", "size", "instruction_count")
    }


def _hash_groups(records):
    groups = defaultdict(list)
    for record in records.values():
        if record["assembly_sha256"]:
            groups[record["assembly_sha256"]].append(_summary(record))
    return [
        {"assembly_sha256": digest, "functions": sorted(functions, key=lambda item: item["address"])}
        for digest, functions in sorted(groups.items())
        if len(functions) > 1
    ]


def _structural_matches(baseline, candidate, threshold, limit):
    candidate_by_token = defaultdict(set)
    for address, record in candidate.items():
        for value in record["imports"]:
            candidate_by_token[("import", value)].add(address)
        for value in record["strings"]:
            candidate_by_token[("string", value)].add(address)

    matches = []
    for left in baseline.values():
        possible = set()
        for value in left["imports"]:
            possible.update(candidate_by_token[("import", value)])
        for value in left["strings"]:
            possible.update(candidate_by_token[("string", value)])
        for candidate_address in possible:
            right = candidate[candidate_address]
            if left["assembly_sha256"] and left["assembly_sha256"] == right["assembly_sha256"]:
                continue
            shared_imports = sorted(set(left["imports"]) & set(right["imports"]))
            shared_strings = sorted(set(left["strings"]) & set(right["strings"]))
            import_score = _jaccard(left["imports"], right["imports"])
            string_score = _jaccard(left["strings"], right["strings"])
            shape_score = _shape_similarity(left, right)
            score = round((0.35 * import_score) + (0.45 * string_score) + (0.20 * shape_score), 4)
            if score < threshold:
                continue
            matches.append({
                "score": score,
                "shared_imports": shared_imports,
                "shared_strings": shared_strings,
                "shape_similarity": shape_score,
                "baseline": _summary(left),
                "candidate": _summary(right),
            })
    matches.sort(key=lambda item: (-item["score"], item["baseline"]["address"], item["candidate"]["address"]))
    return matches[:limit], len(matches)


def compare(baseline_export, candidate_export, threshold=0.75, limit=200):
    """Build a bounded, deterministic comparison report for two exports."""

    threshold = max(0.0, min(float(threshold), 1.0))
    limit = max(1, min(int(limit), 1000))
    baseline_store = LocalEvidenceStore(baseline_export)
    candidate_store = LocalEvidenceStore(candidate_export)
    baseline = _function_records(baseline_store)
    candidate = _function_records(candidate_store)
    candidate_by_hash = defaultdict(list)
    for record in candidate.values():
        if record["assembly_sha256"]:
            candidate_by_hash[record["assembly_sha256"]].append(record)

    exact_matches = []
    for left in baseline.values():
        for right in candidate_by_hash.get(left["assembly_sha256"], []):
            exact_matches.append({"baseline": _summary(left), "candidate": _summary(right)})
    exact_matches.sort(key=lambda item: (item["baseline"]["address"], item["candidate"]["address"]))
    structural_matches, structural_count = _structural_matches(baseline, candidate, threshold, limit)

    return {
        "schema_version": 1,
        "kind": "re-evidence-export-comparison",
        "created_utc": _utc_now(),
        "confidence_rule": (
            "Matching assembly hashes identify identical exported function hashes. "
            "Structural matches are investigation leads only; neither proves shared source or equivalent behaviour."
        ),
        "baseline": baseline_store.status(),
        "candidate": candidate_store.status(),
        "parameters": {"structural_threshold": threshold, "result_limit": limit},
        "summary": {
            "baseline_function_count": len(baseline),
            "candidate_function_count": len(candidate),
            "exact_hash_match_count": len(exact_matches),
            "structural_match_count": structural_count,
            "structural_matches_returned": len(structural_matches),
        },
        "baseline_exact_clone_groups": _hash_groups(baseline),
        "candidate_exact_clone_groups": _hash_groups(candidate),
        "exact_hash_matches": exact_matches[:limit],
        "structural_match_leads": structural_matches,
    }


def default_output(baseline_export, candidate_export):
    baseline_name = os.path.basename(os.path.abspath(baseline_export))
    return os.path.join(os.path.abspath(candidate_export), "derived", "comparisons", "{}.json".format(_slug(baseline_name)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare two exports using exact hashes and conservative structural evidence.")
    parser.add_argument("baseline_export")
    parser.add_argument("candidate_export")
    parser.add_argument("--threshold", type=float, default=0.75, help="Structural lead score from 0 to 1 (default: 0.75).")
    parser.add_argument("--limit", type=int, default=200, help="Maximum exact and structural results to retain (default: 200).")
    parser.add_argument("--output", help="Defaults to <candidate>/derived/comparisons/<baseline>.json")
    args = parser.parse_args(argv)
    try:
        report = compare(args.baseline_export, args.candidate_export, args.threshold, args.limit)
        output = os.path.abspath(args.output or default_output(args.baseline_export, args.candidate_export))
        with locked_file(output):
            _write_json(output, report)
        print("Wrote {} ({} exact matches, {} structural leads).".format(
            output, report["summary"]["exact_hash_match_count"], report["summary"]["structural_match_count"]))
        return 0
    except (EvidenceError, OSError, ValueError, json.JSONDecodeError) as error:
        print("[ERROR] " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
