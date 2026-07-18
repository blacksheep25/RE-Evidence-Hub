"""Disposable, per-run function-name candidates and explicit promotion.

Unattended/local models write here, never to the accepted annotation overlay.
Each run is isolated under ``agent_runs/<run-id>`` and can be deleted safely.
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile
from typing import Any, Dict

from tools.function_annotations import annotate
from tools.investigation_ledger import run_directory
from tools.agent_evidence import validate_annotation_proposal, verify_evidence_refs
from tools.file_lock import locked_file


FILE_NAME = "name_candidates.json"
SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def candidate_path(export_path: str, run_id: str) -> str:
    return os.path.join(run_directory(export_path, run_id), FILE_NAME)


def load(export_path: str, run_id: str) -> Dict[str, Any]:
    path = candidate_path(export_path, run_id)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
        if data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("entries"), dict):
            raise ValueError("Unsupported naming-candidate file: " + path)
        return data
    return {"schema_version": SCHEMA_VERSION, "run_id": run_id, "created_utc": _utc_now(), "revision": 0, "entries": {}}


def _save(export_path: str, run_id: str, data: Dict[str, Any]) -> None:
    path = candidate_path(export_path, run_id)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    data["updated_utc"] = _utc_now()
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=".candidates-", suffix=".tmp", delete=False)
    try:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(handle.name, path)
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)


def propose(export_path: str, run_id: str, lookup: Dict[str, Any], proposal: Dict[str, Any]) -> Dict[str, Any]:
    function = lookup.get("function", {})
    address = function.get("address", "")
    entry = {
        "address": address,
        "raw_name": function.get("raw_name", ""),
        "proposed_name": str(proposal.get("name", "")).strip(),
        "confidence": proposal.get("confidence", ""),
        "evidence": list(proposal.get("evidence", []) or []),
        "evidence_refs": list(proposal.get("evidence_refs", []) or []),
        "rationale": proposal.get("rationale", ""),
        "function_identity": {"assembly_sha256": function.get("hash", "")},
        "status": "pending",
        "created_utc": _utc_now(),
    }
    with locked_file(candidate_path(export_path, run_id)):
        data = load(export_path, run_id)
        previous = data["entries"].get(address)
        if previous:
            snapshot = {key: value for key, value in previous.items() if key != "history"}
            entry["history"] = list(previous.get("history", [])) + [snapshot]
        data["entries"][address] = entry
        data["revision"] = int(data.get("revision", 0)) + 1
        _save(export_path, run_id, data)
    return dict(entry, run_id=run_id, path=candidate_path(export_path, run_id))


def queue(export_path: str, run_id: str, status: str = "pending") -> Dict[str, Any]:
    data = load(export_path, run_id)
    entries = [value for _, value in sorted(data["entries"].items()) if not status or value.get("status") == status]
    return {"run_id": run_id, "path": candidate_path(export_path, run_id), "count": len(entries), "candidates": entries}


def review(store: Any, run_id: str, address: str, action: str, note: str = "") -> Dict[str, Any]:
    if action not in ("accept", "reject"):
        raise ValueError("action must be accept or reject")
    resolved = store.resolve_address(address)
    with locked_file(candidate_path(store.export_path, run_id)):
        data = load(store.export_path, run_id)
        entry = data["entries"].get(resolved)
        if not entry:
            raise ValueError("No candidate for {} in run {}".format(resolved, run_id))
        if entry.get("status") != "pending":
            raise ValueError("Candidate is already {}".format(entry.get("status", "reviewed")))

        if action == "accept":
            current = store.lookup(resolved, include_decompiler=True)
            saved_hash = entry.get("function_identity", {}).get("assembly_sha256", "")
            current_hash = current.get("function", {}).get("hash", "")
            if saved_hash and current_hash and saved_hash != current_hash:
                raise ValueError("Candidate is stale: function identity changed; re-investigate before accepting")
            refs = entry.get("evidence_refs", []) or []
            grounded, missing = verify_evidence_refs(current, refs)
            if not grounded:
                raise ValueError("Candidate evidence is no longer grounded: {}".format(", ".join(missing) or "no usable refs"))
            valid, reason = validate_annotation_proposal(
                entry.get("proposed_name", ""), entry.get("confidence", ""),
                entry.get("evidence", []) or [], entry.get("rationale", ""), refs,
            )
            if not valid:
                raise ValueError("Candidate no longer passes review policy: " + reason)
            result = annotate(
                store.export_path, resolved, entry["proposed_name"], entry["confidence"],
                status="accepted", source="candidate-review:{}".format(run_id),
                evidence=entry.get("evidence", []), rationale=entry.get("rationale", ""),
            )
            store.reload_annotations()
        else:
            result = {"address": resolved, "name": entry.get("proposed_name", ""), "status": "rejected"}

        entry["status"] = "accepted" if action == "accept" else "rejected"
        entry["review_note"] = note or ""
        entry["reviewed_utc"] = _utc_now()
        data["entries"][resolved] = entry
        data["revision"] = int(data.get("revision", 0)) + 1
        _save(store.export_path, run_id, data)
    return dict(result, run_id=run_id, candidate_status=entry["status"])
