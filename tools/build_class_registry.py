"""Build a conservative class and vtable registry from an exported binary.

This is a derived review aid, not a Ghidra symbol importer.  It records a
class-to-vtable association only when an accepted annotation explicitly names
the vtable address in its retained evidence.  Generic ``vftable`` globals and
RTTI/class strings are preserved as discovery evidence but never promoted into
class ownership by this tool.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone


if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.function_annotations import ANNOTATIONS_FILE, ANNOTATIONS_DIR


OUTPUT_NAME = "class_registry.json"
RTTI_PATTERN = re.compile(r"\.\?AV([A-Za-z_][A-Za-z0-9_]*)@@")
CLASS_STRING_PATTERN = re.compile(r"^C[A-Za-z][A-Za-z0-9_]*$")
METHOD_PATTERN = re.compile(r"^(C[A-Za-z][A-Za-z0-9]*)_(.+)$")
VTABLE_PATTERN = re.compile(r"\bvf?table\s+at\s+(?:0x)?([0-9a-fA-F]{8})\b", re.IGNORECASE)


def load_json(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _accepted_decision(entry):
    active_name = entry.get("active_name", "")
    if not active_name:
        return None
    return next(
        (item for item in reversed(entry.get("decisions", []))
         if item.get("name") == active_name and item.get("status") == "accepted"),
        None,
    )


def _global_summary(global_item):
    return {
        "address": global_item.get("address", ""),
        "name": global_item.get("name", ""),
        "datatype": global_item.get("datatype", ""),
        "size": global_item.get("size"),
        "functions": global_item.get("functions", []),
        "references": global_item.get("references", []),
    }


def build_registry(export_path):
    export_path = os.path.abspath(export_path)
    manifest = load_json(os.path.join(export_path, "manifest.json"))
    globals_path = os.path.join(export_path, "globals.json")
    globals_data = load_json(globals_path) if os.path.isfile(globals_path) else []
    if isinstance(globals_data, dict):
        globals_data = list(globals_data.values())
    globals_by_address = {str(item.get("address", "")).lower(): item for item in globals_data if isinstance(item, dict)}

    annotation_path = os.path.join(export_path, ANNOTATIONS_DIR, ANNOTATIONS_FILE)
    overlay = load_json(annotation_path) if os.path.isfile(annotation_path) else {"entries": {}}
    classes = defaultdict(lambda: {
        "accepted_methods": [], "rtti_type_descriptors": [], "class_strings": [], "vtables": [],
    })

    for item in globals_data:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", ""))
        for class_name in RTTI_PATTERN.findall(value):
            classes[class_name]["rtti_type_descriptors"].append(_global_summary(item))
        if CLASS_STRING_PATTERN.fullmatch(value):
            classes[value]["class_strings"].append(_global_summary(item))

    for address, entry in overlay.get("entries", {}).items():
        decision = _accepted_decision(entry)
        if not decision:
            continue
        matched = METHOD_PATTERN.match(str(entry.get("active_name", "")))
        if not matched:
            continue
        class_name, method_name = matched.groups()
        record = {
            "address": address,
            "active_name": entry.get("active_name", ""),
            "method": method_name,
            "confidence": decision.get("confidence", ""),
            "evidence": decision.get("evidence", []),
            "source": decision.get("source", ""),
        }
        classes[class_name]["accepted_methods"].append(record)

        for evidence in decision.get("evidence", []):
            for vtable_address in VTABLE_PATTERN.findall(str(evidence)):
                canonical = vtable_address.lower()
                global_item = globals_by_address.get(canonical)
                if global_item is None:
                    continue
                candidate = {
                    "address": global_item.get("address", vtable_address),
                    "association": "explicit accepted-annotation evidence",
                    "evidence": str(evidence),
                    "global": _global_summary(global_item),
                    "methods_supported_by_this_evidence": [address],
                }
                existing = next((value for value in classes[class_name]["vtables"]
                                 if str(value.get("address", "")).lower() == canonical), None)
                if existing:
                    if address not in existing["methods_supported_by_this_evidence"]:
                        existing["methods_supported_by_this_evidence"].append(address)
                else:
                    classes[class_name]["vtables"].append(candidate)

    normalised_by_casefold = {}
    for class_name in sorted(classes, key=lambda name: (name.lower(), name)):
        value = classes[class_name]
        if not any(value.values()):
            continue
        key = class_name.lower()
        target = normalised_by_casefold.get(key)
        if target is None:
            target = {"name": class_name, "aliases": [class_name], **value}
            normalised_by_casefold[key] = target
        else:
            target["aliases"].append(class_name)
            for field in ("accepted_methods", "rtti_type_descriptors", "class_strings", "vtables"):
                target[field].extend(value[field])

    normalised = []
    for value in normalised_by_casefold.values():
        for key in ("accepted_methods", "rtti_type_descriptors", "class_strings", "vtables"):
            value[key].sort(key=lambda item: str(item.get("address", "")))
        value["aliases"].sort()
        normalised.append(value)
    normalised.sort(key=lambda item: (item["name"].lower(), item["name"]))

    generic_vtables = sum(
        1 for item in globals_data
        if isinstance(item, dict) and "vftable" in str(item.get("name", "")).lower()
    )
    return {
        "schema_version": 1,
        "kind": "ghidra-derived-class-vtable-registry",
        "generated_utc": utc_now(),
        "target": {
            "name": manifest.get("binary", {}).get("name", ""),
            "image_base": manifest.get("binary", {}).get("image_base", ""),
        },
        "rules": {
            "active_names": "Only accepted entries in annotations/function_names.json are listed as methods.",
            "vtable_associations": "Only an explicit accepted annotation mentioning a vtable address creates a class-to-vtable association.",
            "discovery_evidence": "RTTI descriptors and class strings are leads, not proof of ownership or virtual-slot mapping.",
        },
        "summary": {
            "class_count": len(normalised),
            "accepted_method_count": sum(len(value["accepted_methods"]) for value in normalised),
            "explicit_vtable_count": sum(len(value["vtables"]) for value in normalised),
            "generic_vftable_global_count": generic_vtables,
        },
        "classes": normalised,
    }


def save_registry(export_path, registry, output_path=None):
    path = output_path or os.path.join(export_path, OUTPUT_NAME)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(registry, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a conservative derived class/vtable registry.")
    parser.add_argument("export_path")
    parser.add_argument("--output", help="Defaults to <export>/class_registry.json")
    args = parser.parse_args(argv)
    registry = build_registry(args.export_path)
    path = save_registry(os.path.abspath(args.export_path), registry, args.output)
    print("Wrote {} ({} classes, {} explicit vtables).".format(
        path, registry["summary"]["class_count"], registry["summary"]["explicit_vtable_count"]
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
