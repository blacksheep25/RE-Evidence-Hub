#!/usr/bin/env python3
"""Audit and safely migrate mutable derived-artifact schemas."""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import shutil
import tempfile
from typing import Any, Dict, List, Tuple

from tools.file_lock import locked_file


SUPPORTED = {
    "function_names.json": ("ghidra-function-name-overlay", 1),
    "name_candidates.json": (None, 1),
    "investigation_progress.json": (None, 1),
    "runtime_capture.json": ("network-runtime-observations", 1),
    "protocol_contract.json": ("reviewed-network-protocol-contract", 1),
    "metadata.json": ("portable-function-semantic-index", 1),
}


def discover(export_path: str) -> List[str]:
    root = os.path.abspath(export_path)
    paths = [
        os.path.join(root, "annotations", "function_names.json"),
        os.path.join(root, "investigation_progress.json"),
        os.path.join(root, "derived", "network", "runtime_capture.json"),
        os.path.join(root, "derived", "network", "protocol_contract.json"),
        os.path.join(root, "derived", "semantic", "metadata.json"),
    ]
    paths.extend(glob.glob(os.path.join(root, "agent_runs", "*", "name_candidates.json")))
    paths.extend(glob.glob(os.path.join(root, "agent_runs", "*", "investigation_progress.json")))
    return sorted(path for path in paths if os.path.isfile(path))


def audit(export_path: str) -> Dict[str, Any]:
    artifacts = []
    unsupported = 0
    for path in discover(export_path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
        expected_kind, expected_version = SUPPORTED[os.path.basename(path)]
        version = data.get("schema_version")
        kind = data.get("kind")
        valid = version == expected_version and (expected_kind is None or kind == expected_kind)
        unsupported += not valid
        artifacts.append({"path": path, "kind": kind, "schema_version": version, "supported": valid})
    return {"export_path": os.path.abspath(export_path), "artifact_count": len(artifacts), "unsupported": unsupported, "artifacts": artifacts}


def _atomic_json(path: str, data: Dict[str, Any]) -> None:
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=os.path.dirname(path), prefix=".migrate-", suffix=".tmp", delete=False)
    try:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(handle.name, path)
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)


def migrate(export_path: str, backup_root: str = "") -> Dict[str, Any]:
    """Migrate only recognizable legacy v0/missing-version artifacts to v1."""

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.abspath(backup_root or os.path.join(export_path, "artifact_backups", timestamp))
    changed = []
    refused = []
    for path in discover(export_path):
        expected_kind, expected_version = SUPPORTED[os.path.basename(path)]
        with locked_file(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                data = json.load(handle)
            version = data.get("schema_version")
            if version == expected_version and (expected_kind is None or data.get("kind") == expected_kind):
                continue
            recognizable = isinstance(data.get("entries"), dict) and os.path.basename(path) in ("name_candidates.json", "investigation_progress.json")
            if version not in (None, 0) or not recognizable:
                refused.append(path)
                continue
            relative = os.path.relpath(path, os.path.abspath(export_path))
            backup_path = os.path.join(backup, relative)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(path, backup_path)
            data["schema_version"] = 1
            data["migrated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _atomic_json(path, data)
            changed.append({"path": path, "backup": backup_path})
    return {"changed": changed, "refused": refused, "backup_root": backup if changed else None}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit or migrate mutable derived-artifact schemas.")
    parser.add_argument("export_path")
    parser.add_argument("--apply", action="store_true", help="Apply supported v0-to-v1 migrations with backups.")
    parser.add_argument("--backup-root", default="")
    args = parser.parse_args(argv)
    result = migrate(args.export_path, args.backup_root) if args.apply else audit(args.export_path)
    print(json.dumps(result, indent=2))
    return 1 if result.get("unsupported") or result.get("refused") else 0


if __name__ == "__main__":
    raise SystemExit(main())
