"""
Maintain a reversible, evidence-backed function-name overlay for a Ghidra export.

The overlay never changes functions/<address>.json, index.json, or the Ghidra
database. Delete <export>/annotations/ to remove every local naming decision.

Usage:
    python tools/function_annotations.py init <export-folder>
    python tools/function_annotations.py set <export-folder> <address> <name> --confidence high --evidence "..."
    python tools/function_annotations.py list <export-folder>
    python tools/function_annotations.py validate <export-folder>
    python tools/function_annotations.py render <export-folder>
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import tempfile

from tools.file_lock import locked_file


SCHEMA_VERSION = 1
ANNOTATIONS_DIR = "annotations"
ANNOTATIONS_FILE = "function_names.json"
MARKDOWN_FILE = "function_names.md"
CONFIDENCE_LEVELS = ("low", "medium", "high")
STATUS_LEVELS = ("proposed", "accepted", "superseded", "rejected")


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    directory = os.path.dirname(path) or "."
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=directory,
        prefix=".annotations-", suffix=".tmp", delete=False,
    )
    try:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(handle.name, path)
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def annotation_paths(export_path):
    directory = os.path.join(export_path, ANNOTATIONS_DIR)
    return directory, os.path.join(directory, ANNOTATIONS_FILE), os.path.join(directory, MARKDOWN_FILE)


def target_identity(manifest):
    binary = manifest.get("binary", {})
    identity = {
        "program_name": binary.get("name", ""),
        "image_base": binary.get("image_base", ""),
        "language": manifest.get("language", {}).get("id", ""),
        "function_count": manifest.get("functions", {}).get("count"),
    }
    serialized = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    identity["export_identity_sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return identity


def function_identity(function):
    return {
        "address": function.get("address", ""),
        "assembly_sha256": function.get("hash", ""),
        "range": function.get("range", {}),
        "size": function.get("size"),
    }


def new_overlay(manifest):
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "ghidra-function-name-overlay",
        "created_utc": utc_now(),
        "revision": 0,
        "target": target_identity(manifest),
        "conventions": {
            "identifier_style": "PascalCase",
            "recommended_shape": "Subsystem_VerbObjectQualifier",
            "confidence_rule": "Use high only when direct assembly, API, string, or data evidence establishes the behaviour.",
            "scope_rule": "Do not imply a class, protocol, or game feature without direct evidence.",
        },
        "entries": {},
    }


def load_export(export_path):
    export_path = os.path.abspath(export_path)
    manifest_path = os.path.join(export_path, "manifest.json")
    index_path = os.path.join(export_path, "index.json")
    if not os.path.isfile(manifest_path) or not os.path.isfile(index_path):
        raise ValueError("Export must contain manifest.json and index.json: {}".format(export_path))
    return export_path, load_json(manifest_path), load_json(index_path)


def load_overlay(export_path, manifest, create=False):
    directory, overlay_path, _ = annotation_paths(export_path)
    if os.path.isfile(overlay_path):
        overlay = load_json(overlay_path)
        if overlay.get("schema_version") != SCHEMA_VERSION or overlay.get("kind") != "ghidra-function-name-overlay":
            raise ValueError("Unsupported annotation overlay: {}".format(overlay_path))
        return overlay
    if not create:
        raise ValueError("No annotation overlay found. Run init first.")
    os.makedirs(directory, exist_ok=True)
    return new_overlay(manifest)


def save_overlay(export_path, overlay):
    directory, overlay_path, _ = annotation_paths(export_path)
    os.makedirs(directory, exist_ok=True)
    write_json(overlay_path, overlay)


def resolve_address(index, requested):
    functions = index.get("functions", {})
    if requested in functions:
        return requested
    matches = [address for address in functions if address.lower() == requested.lower()]
    if len(matches) == 1:
        return matches[0]
    raise ValueError("Function address not found in index: {}".format(requested))


def load_function(export_path, index, address):
    canonical_address = resolve_address(index, address)
    relative_path = index["functions"][canonical_address].get("file", "functions/{}.json".format(canonical_address))
    path = os.path.join(export_path, relative_path)
    if not os.path.isfile(path):
        raise ValueError("Function record is missing: {}".format(path))
    return canonical_address, load_json(path)


def render_markdown(export_path, overlay):
    _, _, markdown_path = annotation_paths(export_path)
    entries = overlay.get("entries", {})
    lines = [
        "# Function-name overlay",
        "",
        "This is a derived view of `function_names.json`. Delete the `annotations` folder to remove the overlay; raw exports and Ghidra symbols are unchanged.",
        "",
        "| Address | Active name | Confidence | Status | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for address in sorted(entries):
        entry = entries[address]
        active = entry.get("active_name", "")
        decisions = entry.get("decisions", [])
        active_decision = next((item for item in reversed(decisions) if item.get("name") == active), {})
        evidence = "; ".join(active_decision.get("evidence", []))
        lines.append("| `{}` | `{}` | {} | {} | {} |".format(
            address,
            active,
            active_decision.get("confidence", ""),
            active_decision.get("status", ""),
            evidence.replace("|", "\\|"),
        ))
    with open(markdown_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def command_init(args):
    export_path, manifest, _ = load_export(args.export_path)
    _, overlay_path, _ = annotation_paths(export_path)
    with locked_file(overlay_path):
        if os.path.exists(overlay_path) and not args.force:
            raise ValueError("Overlay already exists: {} (use --force only to replace it)".format(overlay_path))
        overlay = new_overlay(manifest)
        save_overlay(export_path, overlay)
        render_markdown(export_path, overlay)
    print("Created {}".format(overlay_path))


def annotate(export_path, address, name, confidence, status="accepted",
             source="manual-analysis", evidence=None, rationale="", reviewer="",
             create=True):
    """Record one evidence-backed function-name decision in the reversible overlay.

    Programmatic entry point shared by the ``set`` CLI command and agent
    adapters (e.g. the MCP write tool). With ``create=True`` (the default) the
    overlay is created on first use so callers need no separate ``init`` step.
    Returns a small result dict; never touches raw export files.
    """
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError("Invalid confidence: {}".format(confidence))
    if status not in STATUS_LEVELS:
        raise ValueError("Invalid status: {}".format(status))

    export_path, manifest, index = load_export(export_path)
    _, overlay_path, _ = annotation_paths(export_path)
    with locked_file(overlay_path):
        overlay = load_overlay(export_path, manifest, create=create)
        address, function = load_function(export_path, index, address)
        entries = overlay.setdefault("entries", {})
        entry = entries.setdefault(address, {"decisions": []})

        now = utc_now()
        decision = {
            "name": name,
            "status": status,
            "confidence": confidence,
            "source": source,
            "reviewer": reviewer or "",
            "created_utc": now,
            "function_identity": function_identity(function),
            "evidence": list(evidence or []),
            "rationale": rationale or "",
        }
        entry.setdefault("decisions", []).append(decision)
        if status == "accepted":
            previous_active = entry.get("active_name", "")
            if previous_active and previous_active != name:
                for previous in reversed(entry["decisions"][:-1]):
                    if previous.get("name") == previous_active and previous.get("status") == "accepted":
                        previous["status"] = "superseded"
                        previous["superseded_utc"] = now
                        previous["superseded_by"] = name
                        break
            entry["active_name"] = name

        overlay["revision"] = int(overlay.get("revision", 0)) + 1
        overlay["updated_utc"] = utc_now()
        save_overlay(export_path, overlay)
        render_markdown(export_path, overlay)
    return {
        "address": address,
        "name": name,
        "raw_name": function.get("name", ""),
        "confidence": confidence,
        "status": status,
    }


def history(export_path, address):
    """Return the complete, non-promoting decision history for one function."""

    export_path, manifest, index = load_export(export_path)
    try:
        overlay = load_overlay(export_path, manifest, create=False)
    except ValueError as error:
        if not str(error).startswith("No annotation overlay found."):
            raise
        overlay = new_overlay(manifest)
    address, function = load_function(export_path, index, address)
    entry = overlay.get("entries", {}).get(address, {})
    current_identity = function_identity(function)
    decisions = []
    for decision in entry.get("decisions", []):
        item = dict(decision)
        item["is_active"] = item.get("name") == entry.get("active_name") and item.get("status") == "accepted"
        saved_identity = item.get("function_identity", {})
        item["evidence_stale"] = bool(
            saved_identity.get("assembly_sha256")
            and saved_identity.get("assembly_sha256") != current_identity.get("assembly_sha256")
        )
        decisions.append(item)
    return {
        "address": address,
        "raw_name": function.get("name", ""),
        "active_name": entry.get("active_name"),
        "current_function_identity": current_identity,
        "overlay_revision": overlay.get("revision", 0),
        "decisions": decisions,
    }


def command_set(args):
    # CLI keeps requiring an explicit `init` (create=False); agent callers use
    # annotate(create=True) directly.
    result = annotate(
        args.export_path, args.address, args.name, args.confidence,
        status=args.status, source=args.source,
        evidence=args.evidence, rationale=args.rationale, reviewer=args.reviewer,
        create=False,
    )
    print("{} -> {} ({}, {})".format(
        result["address"], result["name"], result["confidence"], result["status"]))


def command_history(args):
    print(json.dumps(history(args.export_path, args.address), indent=2, sort_keys=True))


def command_list(args):
    export_path, manifest, _ = load_export(args.export_path)
    overlay = load_overlay(export_path, manifest, create=False)
    entries = overlay.get("entries", {})
    if not entries:
        print("No annotated functions.")
        return
    for address in sorted(entries):
        entry = entries[address]
        active = entry.get("active_name", "")
        decision = next((item for item in reversed(entry.get("decisions", [])) if item.get("name") == active), {})
        print("{}  {}  {}  {}".format(
            address,
            active or "<no accepted name>",
            decision.get("confidence", ""),
            decision.get("status", ""),
        ))


def command_validate(args):
    export_path, manifest, index = load_export(args.export_path)
    overlay = load_overlay(export_path, manifest, create=False)
    errors = []
    warnings = []
    if overlay.get("target") != target_identity(manifest):
        warnings.append("Target identity differs from the export used to create this overlay.")

    for address, entry in sorted(overlay.get("entries", {}).items()):
        try:
            canonical, function = load_function(export_path, index, address)
        except ValueError as error:
            errors.append(str(error))
            continue
        if canonical != address:
            warnings.append("{} is not stored with the index's canonical address {}.".format(address, canonical))
        current_identity = function_identity(function)
        for decision in entry.get("decisions", []):
            saved_identity = decision.get("function_identity", {})
            if saved_identity.get("assembly_sha256") != current_identity.get("assembly_sha256"):
                warnings.append("{} name '{}' is stale: exported assembly hash changed.".format(address, decision.get("name", "")))

    for warning in warnings:
        print("[WARN] " + warning)
    for error in errors:
        print("[ERROR] " + error)
    if errors:
        return 1
    print("Annotation validation passed: {} function(s), {} warning(s).".format(len(overlay.get("entries", {})), len(warnings)))
    return 0


def command_render(args):
    export_path, manifest, _ = load_export(args.export_path)
    overlay = load_overlay(export_path, manifest, create=False)
    render_markdown(export_path, overlay)
    print("Rendered {}".format(annotation_paths(export_path)[2]))


def build_parser():
    parser = argparse.ArgumentParser(description="Maintain a reversible Ghidra function-name overlay.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create an empty annotations overlay.")
    init.add_argument("export_path")
    init.add_argument("--force", action="store_true", help="Replace an existing overlay.")
    init.set_defaults(handler=command_init)

    set_name = subparsers.add_parser("set", help="Record one evidence-backed function name.")
    set_name.add_argument("export_path")
    set_name.add_argument("address")
    set_name.add_argument("name")
    set_name.add_argument("--confidence", choices=CONFIDENCE_LEVELS, required=True)
    set_name.add_argument("--status", choices=STATUS_LEVELS, default="accepted")
    set_name.add_argument("--source", default="manual-analysis")
    set_name.add_argument("--reviewer", default="", help="Optional reviewer identity recorded with this decision.")
    set_name.add_argument("--evidence", action="append", help="Repeat for each concrete evidence item.")
    set_name.add_argument("--rationale", default="")
    set_name.set_defaults(handler=command_set)

    history_command = subparsers.add_parser("history", help="Show the decision and correction history for one function.")
    history_command.add_argument("export_path")
    history_command.add_argument("address")
    history_command.set_defaults(handler=command_history)

    list_command = subparsers.add_parser("list", help="List active accepted names.")
    list_command.add_argument("export_path")
    list_command.set_defaults(handler=command_list)

    validate = subparsers.add_parser("validate", help="Validate addresses and detect changed function bodies.")
    validate.add_argument("export_path")
    validate.set_defaults(handler=command_validate)

    render = subparsers.add_parser("render", help="Regenerate the compact Markdown view.")
    render.add_argument("export_path")
    render.set_defaults(handler=command_render)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result = args.handler(args)
        return 0 if result is None else result
    except (IOError, OSError, ValueError, json.JSONDecodeError) as error:
        print("[ERROR] {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
