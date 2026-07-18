#!/usr/bin/env python3
"""Create and validate reviewed protocol-recreation contracts."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import tempfile
from typing import Any, Dict, List

from tools.file_lock import locked_file
from tools.network_reconstruction import build_report


SCHEMA_VERSION = 1
KIND = "reviewed-network-protocol-contract"
RELATIVE_PATH = os.path.join("derived", "network", "protocol_contract.json")
SECTIONS = ("transport", "framing", "serialization", "encryption", "compression", "dispatch", "session_state")


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def contract_path(export_path: str, output: str = "") -> str:
    return os.path.abspath(output or os.path.join(export_path, RELATIVE_PATH))


def build_contract(export_path: str) -> Dict[str, Any]:
    report = build_report(export_path)
    capture_path = os.path.join(export_path, "derived", "network", "runtime_capture.json")
    capture_summary = None
    if os.path.isfile(capture_path):
        with open(capture_path, encoding="utf-8", errors="replace") as handle:
            capture_summary = json.load(handle).get("summary")
    sections = {
        name: {
            "status": "unknown",
            "statement": "",
            "evidence_refs": [],
            "confidence": "",
            "reviewed_by": "",
            "reviewed_utc": "",
        }
        for name in SECTIONS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "created_utc": _utc_now(),
        "target": report["target"],
        "rules": {
            "confirmation": "A confirmed statement requires evidence_refs, confidence, reviewer, and review timestamp.",
            "unknowns": "Leave uncertain fields unknown; do not encode hypotheses as implementation contracts.",
        },
        "static_summary": report["summary"],
        "runtime_summary": capture_summary,
        "sections": sections,
        "messages": [],
        "test_vectors": [],
    }


def validate_contract(contract: Dict[str, Any]) -> List[str]:
    errors = []
    if contract.get("schema_version") != SCHEMA_VERSION or contract.get("kind") != KIND:
        errors.append("unsupported schema_version/kind")
    sections = contract.get("sections", {})
    for name in SECTIONS:
        section = sections.get(name)
        if not isinstance(section, dict):
            errors.append("missing section: " + name)
            continue
        status = section.get("status", "unknown")
        if status not in ("unknown", "observed", "confirmed", "rejected"):
            errors.append("{} has invalid status".format(name))
        if status == "confirmed":
            for field in ("statement", "evidence_refs", "confidence", "reviewed_by", "reviewed_utc"):
                if not section.get(field):
                    errors.append("confirmed {} requires {}".format(name, field))
    for index, message in enumerate(contract.get("messages", [])):
        if not isinstance(message, dict):
            errors.append("message {} is not an object".format(index))
        elif message.get("status") == "confirmed" and not message.get("evidence_refs"):
            errors.append("confirmed message {} requires evidence_refs".format(index))
    return errors


def save_contract(export_path: str, contract: Dict[str, Any], output: str = "", force: bool = False) -> str:
    path = contract_path(export_path, output)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked_file(path):
        if os.path.exists(path) and not force:
            raise ValueError("Contract already exists: {} (use --force only to replace it)".format(path))
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=os.path.dirname(path), prefix=".contract-", suffix=".tmp", delete=False)
        try:
            json.dump(contract, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            os.replace(handle.name, path)
        finally:
            if os.path.exists(handle.name):
                os.remove(handle.name)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create or validate a reviewed protocol contract.")
    parser.add_argument("export_path")
    parser.add_argument("--output", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate", action="store_true", help="Validate the existing contract instead of creating it.")
    args = parser.parse_args(argv)
    path = contract_path(args.export_path, args.output)
    if args.validate:
        with open(path, encoding="utf-8", errors="replace") as handle:
            contract = json.load(handle)
        errors = validate_contract(contract)
        print(json.dumps({"path": path, "valid": not errors, "errors": errors}, indent=2))
        return 1 if errors else 0
    contract = build_contract(args.export_path)
    print(json.dumps({"output": save_contract(args.export_path, contract, args.output, args.force), "validation_errors": validate_contract(contract)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
