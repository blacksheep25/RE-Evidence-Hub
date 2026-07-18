#!/usr/bin/env python3
"""Build a conservative, evidence-backed networking reconstruction pack."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
from collections import defaultdict
from typing import Any, Dict, List

from tools.local_evidence import LocalEvidenceStore


API_STAGES = {
    "setup": ("wsastartup", "socket", "getaddrinfo", "inet_addr", "inet_pton", "htons", "htonl"),
    "connect": ("connect", "wsaconnect", "bind", "listen", "accept"),
    "send": ("send", "sendto", "wsasend", "wsasendto", "ssl_write"),
    "receive": ("recv", "recvfrom", "wsarecv", "wsarecvfrom", "ssl_read"),
    "multiplex": ("select", "wsapoll", "ioctlsocket", "wsaeventselect"),
    "shutdown": ("shutdown", "closesocket", "wsacleanup"),
}
PROTOCOL_TERMS = ("packet", "opcode", "message", "serialize", "deserialize", "encrypt", "decrypt", "compress", "dispatch")
ENDPOINT_RE = re.compile(r"(?:https?://|wss?://|\b(?:\d{1,3}\.){3}\d{1,3}\b|\b[a-z0-9][a-z0-9.-]+\.(?:com|net|org|io|gg|local)\b)(?::\d{1,5})?", re.I)


def _load(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def _stage_for(name: str) -> str:
    lowered = name.lower().lstrip("_").split("@", 1)[0]
    for stage, tokens in API_STAGES.items():
        if lowered in tokens:
            return stage
    return ""


def build_report(export_path: str, limit: int = 500) -> Dict[str, Any]:
    store = LocalEvidenceStore(export_path)
    raw_imports = _load(os.path.join(store.export_path, "imports.json"), [])
    if isinstance(raw_imports, dict):
        raw_imports = list(raw_imports.values())

    functions: Dict[str, Dict[str, Any]] = {}
    stages: Dict[str, List[str]] = defaultdict(list)
    api_evidence = []
    for item in raw_imports if isinstance(raw_imports, list) else []:
        stage = _stage_for(str(item.get("name", "")))
        if not stage:
            continue
        references = []
        for reference in item.get("references", []) or []:
            address = reference.get("address", "")
            if address not in store.functions:
                continue
            references.append(address)
            stages[stage].append(address)
            if address not in functions and len(functions) < max(1, limit):
                lookup = store.lookup(address, include_decompiler=False)
                functions[address] = {
                    "address": address,
                    "raw_name": lookup["function"].get("raw_name", ""),
                    "active_name": lookup["function"].get("active_name"),
                    "imports": [],
                    "strings": [value.get("value", "") for value in lookup["evidence"].get("strings", [])],
                    "callers": [value.get("address", "") for value in lookup["relationships"].get("callers", [])],
                    "callees": [value.get("address", "") for value in lookup["relationships"].get("callees", [])],
                }
            if address in functions:
                functions[address]["imports"].append(item.get("name", ""))
        api_evidence.append({"stage": stage, "name": item.get("name", ""), "library": item.get("library", ""), "functions": sorted(set(references))})

    raw_strings = _load(os.path.join(store.export_path, "strings.json"), [])
    endpoint_leads = []
    protocol_leads = []
    for item in raw_strings if isinstance(raw_strings, list) else []:
        value = str(item.get("value", ""))
        refs = sorted({ref.get("address", "") for ref in item.get("functions", []) if ref.get("address", "")})
        if ENDPOINT_RE.search(value):
            endpoint_leads.append({"value": value, "functions": refs, "status": "static-lead-unverified"})
        matched = sorted({term for term in PROTOCOL_TERMS if term in value.lower()})
        if matched:
            protocol_leads.append({"value": value, "terms": matched, "functions": refs, "status": "static-lead-unverified"})

    stage_summary = {}
    for stage in API_STAGES:
        addresses = sorted(set(stages.get(stage, [])))
        stage_summary[stage] = {"observed": bool(addresses), "functions": addresses}
    unresolved = [
        question for question, observed in (
            ("transport initialisation and address resolution", stage_summary["setup"]["observed"]),
            ("connection establishment and reconnect policy", stage_summary["connect"]["observed"]),
            ("outbound send path", stage_summary["send"]["observed"]),
            ("inbound receive path", stage_summary["receive"]["observed"]),
            ("packet framing and length rules", any("packet" in lead["terms"] for lead in protocol_leads)),
            ("opcode/message dispatch", any(set(lead["terms"]) & {"opcode", "dispatch", "message"} for lead in protocol_leads)),
            ("serialization, encryption, and compression", any(set(lead["terms"]) & {"serialize", "deserialize", "encrypt", "decrypt", "compress"} for lead in protocol_leads)),
        ) if not observed
    ]
    binary = store.status()["binary"]
    capture_path = os.path.join(store.export_path, "derived", "network", "runtime_capture.json")
    runtime_capture = None
    if os.path.isfile(capture_path):
        capture = _load(capture_path, {})
        if isinstance(capture, dict) and capture.get("kind") == "network-runtime-observations":
            runtime_capture = {"path": capture_path, "summary": capture.get("summary", {})}
    return {
        "schema_version": 1,
        "kind": "network-reconstruction-evidence-pack",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target": binary,
        "confidence_rule": "Imports and exported references are observed static evidence. Endpoint/protocol strings are leads. Packet formats and runtime behaviour require trace or code-path verification.",
        "summary": {"network_imports": len(api_evidence), "network_functions": len(functions), "endpoint_leads": len(endpoint_leads), "protocol_string_leads": len(protocol_leads)},
        "stages": stage_summary,
        "api_evidence": api_evidence,
        "functions": [functions[address] for address in sorted(functions)],
        "endpoint_leads": endpoint_leads[:limit],
        "protocol_string_leads": protocol_leads[:limit],
        "unresolved_contracts": unresolved,
        "runtime_capture": runtime_capture,
        "recommended_next_steps": [
            "Verify each stage by following callers/callees and decompiled control flow.",
            "Capture runtime traffic only when authorised, then correlate frames with static send/receive paths.",
            "Record confirmed packet fields/opcodes as reviewed evidence, never by string similarity alone.",
            "Implement recreation code against confirmed contracts and retain fixtures for encode/decode tests.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = ["# Networking reconstruction evidence pack", "", "Target: `{}`".format(report["target"].get("name", "")), "", report["confidence_rule"], "", "## Observed lifecycle", ""]
    lines += ["- {}: {} ({} function(s))".format(stage, "observed" if value["observed"] else "not yet observed", len(value["functions"])) for stage, value in report["stages"].items()]
    lines += ["", "## Network functions", "", "| Address | Name | Imports |", "| --- | --- | --- |"]
    for function in report["functions"]:
        lines.append("| `{}` | `{}` | {} |".format(function["address"], function.get("active_name") or function["raw_name"], ", ".join(function["imports"])))
    lines += ["", "## Unresolved contracts", ""]
    lines += ["- " + item for item in report["unresolved_contracts"]] or ["- None from this static checklist; runtime verification is still required."]
    lines += ["", "## Next steps", ""] + ["{}. {}".format(index, item) for index, item in enumerate(report["recommended_next_steps"], 1)]
    if report.get("runtime_capture"):
        lines += ["", "## Runtime observations", "", "Imported frames: {}".format(report["runtime_capture"]["summary"].get("frame_count", 0))]
    return "\n".join(lines) + "\n"


def save_report(export_path: str, report: Dict[str, Any], output_dir: str = "") -> Dict[str, str]:
    directory = os.path.abspath(output_dir or os.path.join(export_path, "derived", "network"))
    os.makedirs(directory, exist_ok=True)
    json_path = os.path.join(directory, "network_reconstruction.json")
    markdown_path = os.path.join(directory, "network_reconstruction.md")
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    with open(markdown_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_markdown(report))
    return {"json": json_path, "markdown": markdown_path}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build an evidence-backed networking reconstruction pack.")
    parser.add_argument("export_path", help="Ghidra export directory")
    parser.add_argument("--output-dir", default="", help="Output directory (default: <export>/derived/network)")
    parser.add_argument("--limit", type=int, default=500, help="Maximum functions/leads retained")
    args = parser.parse_args(argv)
    report = build_report(args.export_path, args.limit)
    paths = save_report(args.export_path, report, args.output_dir)
    print(json.dumps({"summary": report["summary"], "outputs": paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
