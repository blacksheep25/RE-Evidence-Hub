#!/usr/bin/env python3
"""Import authorised runtime network observations into a portable JSON schema."""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import re
import tempfile
from collections import Counter
from typing import Any, Dict, Iterable, List

from tools.file_lock import locked_file
from tools.local_evidence import LocalEvidenceStore


SCHEMA_VERSION = 1
CAPTURE_RELATIVE_PATH = os.path.join("derived", "network", "runtime_capture.json")
HEX_RE = re.compile(r"^[0-9a-fA-F]*$")


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _read_input(path: str) -> Iterable[Dict[str, Any]]:
    extension = os.path.splitext(path)[1].lower()
    if extension == ".csv":
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as handle:
            yield from csv.DictReader(handle)
        return
    with open(path, encoding="utf-8-sig", errors="replace") as handle:
        if extension in (".jsonl", ".ndjson"):
            for number, line in enumerate(handle, 1):
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("Frame {} is not an object".format(number))
                    yield value
            return
        value = json.load(handle)
    frames = value.get("frames", []) if isinstance(value, dict) else value
    if not isinstance(frames, list):
        raise ValueError("JSON capture must be a frame list or an object with frames")
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("Every capture frame must be an object")
        yield frame


def _integer(value: Any, field: str, minimum: int = 0, maximum: int = 65535) -> Any:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("{} must be an integer".format(field))
    if parsed < minimum or parsed > maximum:
        raise ValueError("{} is outside {}..{}".format(field, minimum, maximum))
    return parsed


def normalize_frame(raw: Dict[str, Any], sequence: int) -> Dict[str, Any]:
    direction = str(raw.get("direction", "unknown")).strip().lower()
    aliases = {"in": "inbound", "rx": "inbound", "out": "outbound", "tx": "outbound"}
    direction = aliases.get(direction, direction)
    if direction not in ("inbound", "outbound", "unknown"):
        raise ValueError("Frame {} has invalid direction".format(sequence))
    payload = re.sub(r"[\s:\-]", "", str(raw.get("payload_hex", raw.get("payload", ""))))
    if len(payload) % 2 or not HEX_RE.fullmatch(payload):
        raise ValueError("Frame {} payload_hex must contain complete hexadecimal bytes".format(sequence))
    payload_length = len(payload) // 2
    declared = _integer(raw.get("length", ""), "length", 0, 2 ** 31 - 1)
    if declared is not None and payload and declared != payload_length:
        raise ValueError("Frame {} length does not match payload_hex".format(sequence))
    return {
        "sequence": sequence,
        "timestamp": str(raw.get("timestamp", "")).strip(),
        "direction": direction,
        "transport": str(raw.get("transport", "tcp")).strip().lower(),
        "stream_id": str(raw.get("stream_id", raw.get("connection", ""))).strip(),
        "local_address": str(raw.get("local_address", "")).strip(),
        "local_port": _integer(raw.get("local_port", ""), "local_port"),
        "remote_address": str(raw.get("remote_address", "")).strip(),
        "remote_port": _integer(raw.get("remote_port", ""), "remote_port"),
        "payload_hex": payload.lower(),
        "length": declared if declared is not None else payload_length,
        "note": str(raw.get("note", "")).strip(),
    }


def build_capture(export_path: str, input_path: str, source: str = "") -> Dict[str, Any]:
    store = LocalEvidenceStore(export_path)
    frames = [normalize_frame(frame, index) for index, frame in enumerate(_read_input(input_path), 1)]
    directions = Counter(frame["direction"] for frame in frames)
    transports = Counter(frame["transport"] for frame in frames)
    endpoints = sorted({
        "{}:{}".format(frame["remote_address"], frame["remote_port"])
        for frame in frames if frame["remote_address"] or frame["remote_port"] is not None
    })
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "network-runtime-observations",
        "generated_utc": _utc_now(),
        "target": store.status()["binary"],
        "source": source or os.path.basename(input_path),
        "authority_rule": "Import only captures you are authorised to inspect. Runtime frames are observations, not decoded protocol claims.",
        "summary": {
            "frame_count": len(frames),
            "payload_bytes": sum(frame["length"] or 0 for frame in frames),
            "directions": dict(sorted(directions.items())),
            "transports": dict(sorted(transports.items())),
            "remote_endpoints": endpoints,
        },
        "frames": frames,
    }


def save_capture(export_path: str, capture: Dict[str, Any], output: str = "") -> str:
    path = os.path.abspath(output or os.path.join(export_path, CAPTURE_RELATIVE_PATH))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked_file(path):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=os.path.dirname(path), prefix=".capture-", suffix=".tmp", delete=False)
        try:
            json.dump(capture, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            os.replace(handle.name, path)
        finally:
            if os.path.exists(handle.name):
                os.remove(handle.name)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import JSON/JSONL/CSV runtime network observations.")
    parser.add_argument("export_path")
    parser.add_argument("input_path")
    parser.add_argument("--source", default="", help="Capture provenance/label.")
    parser.add_argument("--output", default="", help="Default: <export>/derived/network/runtime_capture.json")
    args = parser.parse_args(argv)
    capture = build_capture(args.export_path, args.input_path, args.source)
    path = save_capture(args.export_path, capture, args.output)
    print(json.dumps({"output": path, "summary": capture["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
