"""Build a non-promoting, evidence-backed function-name review queue.

The queue never edits the annotation overlay.  Each suggested name is a low or
medium confidence review candidate based on direct export strings/imports; a
human must inspect the evidence and explicitly record an accepted annotation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.function_annotations import ANNOTATIONS_FILE, ANNOTATIONS_DIR


OUTPUT_NAME = "name_review_queue.json"
NETWORK_IMPORTS = {
    "send": "Send", "sendto": "SendTo", "recv": "Receive", "recvfrom": "ReceiveFrom",
    "connect": "Connect", "bind": "Bind", "listen": "Listen", "accept": "Accept",
    "wsasend": "WsaSend", "wsarecv": "WsaReceive",
}
RESOURCE_PATTERN = re.compile(r"(?:^|[\\/])?([a-z0-9_]+)\.(?:txt|json|xml|ini|cfg)$", re.IGNORECASE)


def load_json(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _candidate_eligible(index, overlay, address):
    function = index.get("functions", {}).get(address, {})
    raw_name = str(function.get("name", ""))
    return raw_name.startswith("FUN_") and not overlay.get("entries", {}).get(address, {}).get("active_name")


def _resource_stem(value):
    candidate = str(value).replace("/", "\\")
    match = RESOURCE_PATTERN.search(candidate)
    return match.group(1) if match else ""


def _pascal(value):
    return "".join(piece[:1].upper() + piece[1:] for piece in re.split(r"[^A-Za-z0-9]+", value) if piece)


def build_review_queue(export_path, limit=250):
    export_path = os.path.abspath(export_path)
    manifest = load_json(os.path.join(export_path, "manifest.json"))
    index = load_json(os.path.join(export_path, "index.json"))
    annotation_path = os.path.join(export_path, ANNOTATIONS_DIR, ANNOTATIONS_FILE)
    overlay = load_json(annotation_path) if os.path.isfile(annotation_path) else {"entries": {}}
    strings_path = os.path.join(export_path, "strings.json")
    imports_path = os.path.join(export_path, "imports.json")
    strings = load_json(strings_path) if os.path.isfile(strings_path) else []
    imports = load_json(imports_path) if os.path.isfile(imports_path) else []
    if isinstance(imports, dict):
        imports = list(imports.values())

    candidates = []
    seen = set()
    for item in imports:
        import_name = str(item.get("name", ""))
        operation = NETWORK_IMPORTS.get(import_name.lower())
        if not operation:
            continue
        for reference in item.get("references", []):
            address = reference.get("address", "")
            key = (address, "network-import", import_name.lower())
            if key in seen or not _candidate_eligible(index, overlay, address):
                continue
            seen.add(key)
            candidates.append({
                "address": address,
                "raw_name": index["functions"][address].get("name", ""),
                "kind": "network-import",
                "proposed_name": "Net_{}".format(operation),
                "confidence": "low",
                "status": "proposed-review-only",
                "evidence": [{"type": "direct-import", "name": import_name, "library": item.get("library", "")}],
                "rationale": "The function directly references {}. This establishes only the imported operation, not its protocol or high-level role.".format(import_name),
            })

    for item in strings:
        value = str(item.get("value", ""))
        stem = _resource_stem(value)
        if not stem:
            continue
        for reference in item.get("functions", []):
            address = reference.get("address", "")
            key = (address, "ui-resource", stem.lower())
            if key in seen or not _candidate_eligible(index, overlay, address):
                continue
            seen.add(key)
            candidates.append({
                "address": address,
                "raw_name": index["functions"][address].get("name", ""),
                "kind": "ui-resource",
                "proposed_name": "UIResource_{}_Related".format(_pascal(stem)),
                "confidence": "low",
                "status": "proposed-review-only",
                "evidence": [{"type": "direct-string", "address": item.get("address", ""), "value": value}],
                "rationale": "The function directly references this resource path. The lifecycle method, owning class, and control role require review before accepting a name.",
            })

    candidates.sort(key=lambda item: (item["kind"], item["address"], item["proposed_name"]))
    candidates = candidates[:max(1, int(limit))]
    return {
        "schema_version": 1,
        "kind": "ghidra-derived-function-name-review-queue",
        "generated_utc": utc_now(),
        "target": {
            "name": manifest.get("binary", {}).get("name", ""),
            "image_base": manifest.get("binary", {}).get("image_base", ""),
        },
        "rules": {
            "non_promotion": "This queue never writes annotations and no proposed_name is an active name.",
            "acceptance": "Inspect the function and record concrete evidence with tools/function_annotations.py before accepting a name.",
            "confidence": "Candidates are deliberately low confidence because direct imports/resources do not establish a complete semantic role.",
        },
        "summary": {"candidate_count": len(candidates), "limit": max(1, int(limit))},
        "candidates": candidates,
    }


def save_review_queue(export_path, queue, output_path=None):
    path = output_path or os.path.join(export_path, OUTPUT_NAME)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(queue, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a non-promoting function-name review queue.")
    parser.add_argument("export_path")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--output", help="Defaults to <export>/name_review_queue.json")
    args = parser.parse_args(argv)
    queue = build_review_queue(args.export_path, args.limit)
    path = save_review_queue(os.path.abspath(args.export_path), queue, args.output)
    print("Wrote {} ({} review candidates).".format(path, queue["summary"]["candidate_count"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
