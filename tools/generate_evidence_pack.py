"""Generate a reviewable, versioned evidence pack for one recreation topic."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from host_config import DEFAULT_EXPORT_PATH
from tools.local_evidence import EvidenceError, LocalEvidenceStore


def slug(value):
    output = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return output or "evidence-pack"


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create a derived evidence pack for one bounded topic.")
    parser.add_argument("title", help="Human-readable topic, for example 'Title Login and Server Select'")
    parser.add_argument("--export", dest="export_path", default=DEFAULT_EXPORT_PATH)
    parser.add_argument("--control", action="append", default=[], help="Repeat for each UI/control-like term")
    parser.add_argument("--asset", action="append", default=[], help="Repeat for each asset/resource term")
    parser.add_argument("--function", action="append", default=[], help="Repeat for an address or accepted function name")
    parser.add_argument("--output", help="Defaults to <export>/evidence_packs/<title>.json")
    args = parser.parse_args(argv)

    try:
        store = LocalEvidenceStore(args.export_path)
        pack = {
            "schema_version": 1,
            "kind": "binary-evidence-pack",
            "title": args.title,
            "created_utc": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
            "target": store.status(),
            "confidence_rule": "Raw export data is evidence. Only accepted annotations establish active semantic names.",
            "controls": [{"term": item, "trace": store.trace(item, "control", 25)} for item in args.control],
            "assets": [{"term": item, "trace": store.trace(item, "asset", 25)} for item in args.asset],
            "functions": [{"identifier": item, "lookup": store.lookup(item, include_decompiler=False, include_assembly=False)} for item in args.function],
        }
        output = args.output or os.path.join(
            store.export_path, "evidence_packs", "{}.json".format(slug(args.title)))
        write_json(os.path.abspath(output), pack)
        print("Wrote {} ({} controls, {} assets, {} functions).".format(
            output, len(args.control), len(args.asset), len(args.function)))
        return 0
    except (EvidenceError, OSError, ValueError, json.JSONDecodeError) as error:
        print("[ERROR] {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
