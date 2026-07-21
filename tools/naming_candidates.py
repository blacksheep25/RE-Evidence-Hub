"""Disposable, per-run function-name candidates and explicit promotion.

Unattended/local models write here, never to the accepted annotation overlay.
Each run is isolated under ``agent_runs/<run-id>`` and can be deleted safely.
"""

from __future__ import annotations

import base64
import binascii
import datetime
import hashlib
import json
import os
import tempfile
from typing import Any, Dict

from tools.function_annotations import annotate
from tools.investigation_ledger import run_directory
from tools.agent_evidence import grounded_evidence_values, validate_annotation_proposal, verify_evidence_refs
from tools.file_lock import locked_file


FILE_NAME = "name_candidates.json"
SCHEMA_VERSION = 1
PREFLIGHT_FILE_NAME = "candidate_preflight.json"
PREFLIGHT_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def candidate_path(export_path: str, run_id: str) -> str:
    return os.path.join(run_directory(export_path, run_id), FILE_NAME)


def preflight_path(export_path: str, run_id: str) -> str:
    return os.path.join(run_directory(export_path, run_id), PREFLIGHT_FILE_NAME)


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


def _load_preflight(export_path: str, run_id: str) -> Dict[str, Any]:
    path = preflight_path(export_path, run_id)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError, UnicodeError, ValueError):
        return {}
    if data.get("schema_version") != PREFLIGHT_SCHEMA_VERSION or not isinstance(data.get("entries"), dict):
        return {}
    return data


def _save_preflight(export_path: str, run_id: str, data: Dict[str, Any]) -> None:
    path = preflight_path(export_path, run_id)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=".preflight-", suffix=".tmp", delete=False)
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


def _triage(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Rank likely useful reviews without treating candidate evidence as truth."""
    references = [str(value) for value in entry.get("evidence_refs", []) or [] if str(value).strip()]
    score = min(len(references), 3)
    reasons = ["{} cited evidence reference(s)".format(len(references))]
    if entry.get("confidence") == "high":
        score += 1
        reasons.append("unverified high-confidence proposal")
    if any("\\" in value or "/" in value for value in references):
        score += 3
        reasons.append("source or asset path reference")
    generic_terms = ("memory", "resource", "invalid", "error", "exception", "helper", "handler", "utility")
    proposed = str(entry.get("proposed_name", "")).lower()
    if any(term in proposed for term in generic_terms):
        score -= 3
        reasons.append("generic proposed-name penalty")
    return {"score": score, "reasons": reasons}


def _generic_name(entry: Dict[str, Any]) -> bool:
    generic_terms = ("memory", "resource", "invalid", "error", "exception", "helper", "handler", "utility")
    proposed = str(entry.get("proposed_name", "")).lower()
    return any(term in proposed for term in generic_terms)


def _candidate_fingerprint(data: Dict[str, Any]) -> str:
    """Hash proposal content while deliberately excluding mutable review state."""
    entries = {
        address: {
            key: entry.get(key)
            for key in ("proposed_name", "confidence", "evidence", "evidence_refs", "rationale", "function_identity")
        }
        for address, entry in sorted((data.get("entries", {}) or {}).items())
    }
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def preflight(store: Any, run_id: str, refresh: bool = False) -> Dict[str, Any]:
    """Build a local-only validation and clustering pass before model review."""
    with locked_file(candidate_path(store.export_path, run_id)):
        candidates = load(store.export_path, run_id)
    existing = _load_preflight(store.export_path, run_id)
    candidate_revision = int(candidates.get("revision", 0))
    candidate_fingerprint = _candidate_fingerprint(candidates)
    if not refresh and existing.get("candidate_fingerprint") == candidate_fingerprint:
        return existing

    name_groups: Dict[str, list] = {}
    for address, entry in candidates["entries"].items():
        key = str(entry.get("proposed_name", "")).strip().lower()
        if key:
            name_groups.setdefault(key, []).append(address)

    entries: Dict[str, Any] = {}
    counts = {"review": 0, "parked": 0, "invalid": 0, "stale": 0}
    for address, entry in candidates["entries"].items():
        lookup = store.lookup(address, include_decompiler=False, include_assembly=False)
        refs = list(entry.get("evidence_refs", []) or [])
        grounded, missing = verify_evidence_refs(lookup, refs)
        policy_valid, policy_reason = validate_annotation_proposal(
            entry.get("proposed_name", ""), entry.get("confidence", ""),
            entry.get("evidence", []) or [], entry.get("rationale", ""), refs,
        )
        saved_hash = str(entry.get("function_identity", {}).get("assembly_sha256", ""))
        current_hash = str(lookup.get("function", {}).get("hash", ""))
        hash_matches = not (saved_hash and current_hash) or saved_hash == current_hash
        duplicate_count = len(name_groups.get(str(entry.get("proposed_name", "")).strip().lower(), []))
        if not hash_matches:
            bucket = "stale"
        elif not grounded or not policy_valid:
            bucket = "invalid"
        elif _generic_name(entry) and duplicate_count >= 3:
            bucket = "parked"
        else:
            bucket = "review"
        counts[bucket] += 1
        entries[address] = {
            "bucket": bucket,
            "hash_matches": hash_matches,
            "grounded": grounded,
            "missing_refs": missing,
            "policy_valid": policy_valid,
            "policy_reason": policy_reason,
            "duplicate_proposed_name_count": duplicate_count,
        }

    clusters = [
        {"proposed_name": candidates["entries"][addresses[0]].get("proposed_name", ""), "count": len(addresses), "addresses": sorted(addresses)[:20]}
        for addresses in name_groups.values() if len(addresses) >= 3
    ]
    clusters.sort(key=lambda item: (-item["count"], item["proposed_name"].lower()))
    result = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "run_id": run_id,
        "candidate_revision": candidate_revision,
        "candidate_fingerprint": candidate_fingerprint,
        "created_utc": _utc_now(),
        "summary": {"candidate_count": len(entries), "buckets": counts, "duplicate_clusters": len(clusters)},
        "duplicate_name_clusters": clusters[:100],
        "entries": entries,
    }
    with locked_file(preflight_path(store.export_path, run_id)):
        previous = _load_preflight(store.export_path, run_id)
        result["revision"] = int(previous.get("revision", 0)) + 1
        _save_preflight(store.export_path, run_id, result)
    return result


def _current_preflight(export_path: str, run_id: str, candidates: Dict[str, Any]) -> Dict[str, Any]:
    value = _load_preflight(export_path, run_id)
    return value if value.get("candidate_fingerprint") == _candidate_fingerprint(candidates) else {}


def _compact_text(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "..."


def _compact_evidence(items: list, limit: int = 8) -> list:
    return [_compact_text(item, 360) for item in (items or [])[:limit]]


def _encode_cursor(score: int, address: str) -> str:
    value = json.dumps({"score": score, "address": address}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple:
    try:
        padded = str(cursor) + "=" * (-len(str(cursor)) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        return -int(value["score"]), str(value["address"])
    except (binascii.Error, KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("Invalid candidate-page cursor") from exc


def page(export_path: str, run_id: str, status: str = "pending",
         limit: int = 25, cursor: str = "", bucket: str = "all") -> Dict[str, Any]:
    """Return a stable page ordered by an explicitly untrusted triage heuristic."""
    if status not in ("pending", "accepted", "rejected", "deferred", "all"):
        raise ValueError("Invalid candidate status: " + status)
    if bucket not in ("review", "parked", "invalid", "stale", "all"):
        raise ValueError("Invalid candidate preflight bucket: " + bucket)
    limit = max(1, min(int(limit), 100))
    data = load(export_path, run_id)
    preflight = _current_preflight(export_path, run_id, data)
    if bucket != "all" and not preflight:
        raise ValueError("No current candidate preflight; call binary_candidate_preflight first")
    entries = [
        dict(entry, triage=_triage(entry), preflight=preflight.get("entries", {}).get(address))
        for address, entry in data["entries"].items()
        if (status == "all" or entry.get("status") == status)
        and (bucket == "all" or preflight.get("entries", {}).get(address, {}).get("bucket") == bucket)
    ]
    entries.sort(key=lambda entry: (-entry["triage"]["score"], entry.get("address", "")))
    total_count = len(entries)
    if cursor:
        cursor_key = _decode_cursor(cursor)
        entries = [entry for entry in entries if (-entry["triage"]["score"], entry.get("address", "")) > cursor_key]
    candidates = entries[:limit]
    next_cursor = ""
    if len(entries) > len(candidates):
        last = candidates[-1]
        next_cursor = _encode_cursor(last["triage"]["score"], last.get("address", ""))
    return {
        "run_id": run_id,
        "path": candidate_path(export_path, run_id),
        "status": status,
        "total_count": total_count,
        "returned_count": len(candidates),
        "remaining_count": len(entries) - len(candidates),
        "next_cursor": next_cursor or None,
        "preflight": {"available": bool(preflight), "bucket": bucket},
        "triage_warning": "Triage scores use unverified candidate metadata only; verify raw function evidence before review.",
        "candidates": candidates,
    }


def review_brief(store: Any, run_id: str, address: str,
                 max_decompiler_chars: int = 4000, relationship_limit: int = 8) -> Dict[str, Any]:
    """Return only the evidence needed for a low-token candidate review."""
    resolved = store.resolve_address(address)
    candidates = load(store.export_path, run_id)
    candidate = candidates["entries"].get(resolved)
    if not candidate:
        raise ValueError("No candidate for {} in run {}".format(resolved, run_id))
    lookup = store.lookup(resolved, include_decompiler=True, include_assembly=False, evidence_limit=12)
    refs = list(candidate.get("evidence_refs", []) or [])
    grounded, missing = verify_evidence_refs(lookup, refs)
    code = str((lookup.get("decompiler", {}) or {}).get("c_code", ""))
    max_decompiler_chars = max(0, min(int(max_decompiler_chars), 12000))
    decompiler = {
        "success": bool((lookup.get("decompiler", {}) or {}).get("success")),
        "c_code": code[:max_decompiler_chars],
        "c_code_truncated": len(code) > max_decompiler_chars,
        "original_c_code_chars": len(code),
    }
    relationship_limit = max(1, min(int(relationship_limit), 20))
    relationships = lookup.get("relationships", {}) or {}
    compact_relationships = {
        direction: [
            {key: item.get(key) for key in ("address", "name", "raw_name", "active_name", "external") if item.get(key) not in (None, "")}
            for item in (relationships.get(direction, []) or [])[:relationship_limit]
        ]
        for direction in ("callers", "callees")
    }
    current_preflight = _current_preflight(store.export_path, run_id, candidates)
    return {
        "run_id": run_id,
        "candidate": {
            "address": candidate.get("address", ""),
            "raw_name": candidate.get("raw_name", ""),
            "proposed_name": candidate.get("proposed_name", ""),
            "confidence": candidate.get("confidence", ""),
            "evidence_refs": _compact_evidence(candidate.get("evidence_refs", [])),
            "evidence": _compact_evidence(candidate.get("evidence", [])),
            "rationale": _compact_text(candidate.get("rationale", ""), 600),
            "status": candidate.get("status", ""),
        },
        "preflight": current_preflight.get("entries", {}).get(resolved),
        "function": {
            key: lookup.get("function", {}).get(key)
            for key in ("address", "raw_name", "active_name", "namespace", "signature", "size", "hash")
        },
        "grounding": {"all_refs_grounded": grounded, "missing_refs": missing, "matched_raw_values": _compact_evidence(grounded_evidence_values(lookup, refs), 12)},
        "evidence": {
            "strings": (lookup.get("evidence", {}) or {}).get("strings", [])[:12],
            "imports": (lookup.get("evidence", {}) or {}).get("imports", [])[:12],
        },
        "relationships": compact_relationships,
        "decompiler": decompiler,
    }


def review(store: Any, run_id: str, address: str, action: str, note: str = "") -> Dict[str, Any]:
    if action not in ("accept", "reject", "defer"):
        raise ValueError("action must be accept, reject, or defer")
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
        elif action == "reject":
            result = {"address": resolved, "name": entry.get("proposed_name", ""), "status": "rejected"}
        else:
            result = {"address": resolved, "name": entry.get("proposed_name", ""), "status": "deferred"}

        entry["status"] = {"accept": "accepted", "reject": "rejected", "defer": "deferred"}[action]
        entry["review_note"] = note or ""
        entry["reviewed_utc"] = _utc_now()
        data["entries"][resolved] = entry
        data["revision"] = int(data.get("revision", 0)) + 1
        _save(store.export_path, run_id, data)
    return dict(result, run_id=run_id, candidate_status=entry["status"])
