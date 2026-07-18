"""Durable, resumable work ledger for autonomous investigation runs.

Tracks per-function progress in ``agent_runs/<run-id>/investigation_progress.json``
(or the legacy export-root location when no run id is supplied), with atomic
writes so an overnight run resumes cleanly after a crash or
restart. It is the "what's done / what's next" companion to the annotation
overlay (the "what was concluded"): together they let an agent stop and resume
without redoing work or losing findings.

Target selection is intentionally simple and deterministic: prefer the curated
name-review-queue candidates, then any remaining unnamed ``FUN_`` function,
always skipping anything already annotated (has an ``active_name``) or recorded
done/skipped. This module has no third-party dependencies.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import tempfile
from typing import Any, Dict, List, Optional


LEDGER_NAME = "investigation_progress.json"
SCHEMA_VERSION = 1
TERMINAL_STATUSES = ("done", "skipped")
STATUSES = ("done", "skipped", "deferred")
# A target attempted this many times (including repeated deferrals) is retired
# from the frontier so an overnight loop can never re-serve it forever.
MAX_ATTEMPTS = 3


def _safe_run_id(run_id: Optional[str]) -> Optional[str]:
    if run_id is None:
        return None
    value = str(run_id).strip()
    if not value or value in (".", "..") or any(char in value for char in '<>:"/\\|?*'):
        raise ValueError("run_id must be a non-empty filesystem-safe name")
    return value


def run_directory(export_path: str, run_id: str) -> str:
    return os.path.join(os.path.abspath(export_path), "agent_runs", _safe_run_id(run_id))


def ledger_path(export_path: str, run_id: Optional[str] = None) -> str:
    base = run_directory(export_path, run_id) if run_id is not None else os.path.abspath(export_path)
    return os.path.join(base, LEDGER_NAME)


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def load(export_path: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    path = ledger_path(export_path, run_id)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and isinstance(data.get("entries"), dict):
                return data
        except (json.JSONDecodeError, OSError, UnicodeError, ValueError):
            # A partial/corrupt ledger (e.g. crash mid-write on a filesystem
            # without atomic replace) must not brick the run: fall through to a
            # fresh ledger, which the next record() call persists over it.
            pass
    return {"schema_version": SCHEMA_VERSION, "created_utc": _utc_now(), "entries": {}}


def _atomic_save(export_path: str, data: Dict[str, Any], run_id: Optional[str] = None) -> None:
    data["updated_utc"] = _utc_now()
    path = ledger_path(export_path, run_id)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=directory, prefix=".progress-", suffix=".tmp", delete=False
    )
    try:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(handle.name, path)
        # Best-effort sweep of temp files orphaned by a previous hard kill.
        for stale in glob.glob(os.path.join(directory, ".progress-*.tmp")):
            try:
                os.remove(stale)
            except OSError:
                pass
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)


def record(export_path: str, address: str, status: str, note: str = "", run_id: Optional[str] = None) -> Dict[str, Any]:
    """Record a terminal/deferred outcome for one target and persist atomically."""
    if status not in STATUSES:
        raise ValueError("Invalid status: {} (expected one of {})".format(status, STATUSES))
    data = load(export_path, run_id)
    entry = data["entries"].get(address, {"attempts": 0})
    entry["status"] = status
    entry["note"] = note or ""
    entry["attempts"] = int(entry.get("attempts", 0)) + 1
    entry["updated_utc"] = _utc_now()
    data["entries"][address] = entry
    _atomic_save(export_path, data, run_id)
    return {"address": address, "status": status, "attempts": entry["attempts"]}


def _annotated_addresses(store: Any) -> set:
    entries = getattr(store, "annotations", {}).get("entries", {})
    return {addr for addr, entry in entries.items() if entry.get("active_name")}


def next_target(store: Any, export_path: str, limit: int = 500, run_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Pick the next function to work on, or None if the frontier is exhausted.

    Skips anything already annotated or recorded done/skipped. Deferred targets
    remain eligible (they are re-served). Read-only: it does not mutate the
    ledger — the agent records the outcome via annotate (done) or record(skip).
    """
    data = load(export_path, run_id)
    blocked = {
        addr for addr, e in data["entries"].items()
        if e.get("status") in TERMINAL_STATUSES or int(e.get("attempts", 0)) >= MAX_ATTEMPTS
    }
    blocked |= _annotated_addresses(store)

    # Priority 1: curated review-queue candidates (concrete naming leads).
    try:
        review = store.review_queue("", limit)
    except Exception:
        review = {"available": False}
    if review.get("available"):
        for candidate in review.get("candidates", []):
            address = candidate.get("address")
            if address and address not in blocked and address in store.functions:
                return {
                    "address": address,
                    "raw_name": store.functions[address].get("name", ""),
                    "reason": "review-queue candidate: {}".format(candidate.get("proposed_name", "")),
                    "attempts": data["entries"].get(address, {}).get("attempts", 0),
                }

    # Priority 2: any remaining unnamed FUN_ function, in address order.
    for address in sorted(store.functions):
        if address in blocked:
            continue
        raw_name = store.functions[address].get("name", "")
        if raw_name.startswith("FUN_"):
            return {
                "address": address,
                "raw_name": raw_name,
                "reason": "unnamed function",
                "attempts": data["entries"].get(address, {}).get("attempts", 0),
            }

    return None


def summary(store: Any, export_path: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    data = load(export_path, run_id)
    by_status: Dict[str, int] = {}
    for entry in data["entries"].values():
        by_status[entry.get("status", "?")] = by_status.get(entry.get("status", "?"), 0) + 1
    total = len(store.functions)
    annotated = _annotated_addresses(store)
    terminal = {addr for addr, entry in data["entries"].items() if entry.get("status") in TERMINAL_STATUSES}
    resolved = annotated | terminal
    return {
        "total_functions": total,
        "annotated": len(annotated),
        "ledger_recorded": len(data["entries"]),
        "by_status": by_status,
        "remaining_estimate": max(0, total - len(resolved)),
        "updated_utc": data.get("updated_utc", ""),
        "run_id": run_id,
    }
