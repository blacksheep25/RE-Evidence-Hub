#!/usr/bin/env python3
"""
revhub: one entry point for the RE-Evidence-Hub host tools.

Subcommands:

  doctor         Preflight check of the host environment and active export.
  use            Show, set, or clear the "current export" pointer.
  query ...      Query the active export (delegates to tools/evidence_tools.py).
  serve ...      Start the HTTP evidence API (binary_agent_server.py).
  mcp ...        Start the stdio MCP adapter (binary_agent_mcp_server.py).
  index ...      Build the FTS body index (tools/build_local_index.py).
  classes ...    Build the class/vtable registry (tools/build_class_registry.py).
  review-queue . Build the name review queue (tools/build_name_review_queue.py).
  validate ...   Validate an export (tools/validate_export.py).

For the positional-path tools (index/classes/review-queue/validate), the active
export is injected automatically when you do not pass a path, so the pointer set
with ``revhub use`` applies everywhere.
"""

from __future__ import annotations

import argparse
import glob
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from importlib import metadata as importlib_metadata


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import host_config


# Subcommand -> (module, function, value_flags).
# value_flags is None for tools that already default --export to
# DEFAULT_EXPORT_PATH (no positional to inject). Otherwise it is the set of
# option flags that consume the following token, so the active export can be
# injected as the positional export path only when the user did not pass one.
DELEGATES = {
    "query": ("tools.evidence_tools", "main", None),
    "serve": ("binary_agent_server", "main", None),
    "mcp": ("binary_agent_mcp_server", "main", None),
    "index": ("tools.build_local_index", "main", {"--output"}),
    "classes": ("tools.build_class_registry", "main", {"--output"}),
    "review-queue": ("tools.build_name_review_queue", "main", {"--output", "--limit"}),
}


# --------------------------------------------------------------------------
# doctor
# --------------------------------------------------------------------------

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"


def _probe_import(module, dist=None):
    """Return (importable, version_string). Version via package metadata."""

    try:
        importlib.import_module(module)
    except Exception as exc:  # ImportError or a transitive failure
        return False, str(exc)
    try:
        return True, importlib_metadata.version(dist or module)
    except Exception:
        return True, ""


def _java_homes_from_install_dirs():
    homes = []
    for base in (
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
    ):
        homes.extend(sorted(glob.glob(os.path.join(base, "jdk-21*")), reverse=True))
    return homes


def _detect_java():
    """Return (java_path, version_line) for the best available java, or (None, None).

    Scans JAVA_HOME, PATH, and known JDK 21 installs and PREFERS a runnable
    JDK 21 across all of them, so a broken or non-21 JAVA_HOME does not mask a
    usable JDK 21 elsewhere (which is what a headless export would actually
    pick up). Falls back to the first runnable java otherwise.
    """

    exe = "java.exe" if os.name == "nt" else "java"
    candidates = []

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(os.path.join(java_home, "bin", exe))

    on_path = shutil.which("java")
    if on_path:
        candidates.append(on_path)

    for home in _java_homes_from_install_dirs():
        candidates.append(os.path.join(home, "bin", exe))

    fallback = None
    for java in candidates:
        if not java or not os.path.isfile(java):
            continue
        try:
            proc = subprocess.run(
                [java, "-version"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            if fallback is None:
                fallback = (java, None)
            continue
        output = proc.stderr or proc.stdout or ""
        line = output.strip().splitlines()[0] if output.strip() else ""
        if _java_major(line) == 21:
            return java, line
        if fallback is None:
            fallback = (java, line)

    return fallback or (None, None)


def _java_major(version_line):
    match = re.search(r'"(\d+)', version_line or "")
    if match:
        return int(match.group(1))
    return None


def _export_checks(export_path, source):
    checks = []

    checks.append(("active export", INFO, "{} [{}]".format(export_path, source)))

    manifest = os.path.join(export_path, "manifest.json")

    if not os.path.isdir(export_path):
        checks.append((
            "export folder",
            WARN,
            "does not exist yet — run an export or `revhub use <export>`",
        ))
        return checks

    if not os.path.isfile(manifest):
        checks.append((
            "export folder",
            WARN,
            "exists but has no manifest.json (not a valid export)",
        ))
        return checks

    try:
        with open(manifest, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        name = data.get("binary", {}).get("name", "?")
        count = data.get("functions", {}).get("count", "?")
        checks.append((
            "export folder",
            PASS,
            "valid export: {} ({} functions)".format(name, count),
        ))
    except (OSError, ValueError) as exc:
        checks.append(("export folder", WARN, "manifest.json unreadable: {}".format(exc)))
        return checks

    derived = [
        ("FTS index", "local_evidence.sqlite3"),
        ("class registry", "class_registry.json"),
        ("name review queue", "name_review_queue.json"),
        ("annotation overlay", os.path.join("annotations", "function_names.json")),
    ]
    present = [label for label, rel in derived if os.path.isfile(os.path.join(export_path, rel))]
    missing = [label for label, rel in derived if not os.path.isfile(os.path.join(export_path, rel))]
    checks.append((
        "derived indexes",
        INFO,
        "present: {} | absent: {}".format(
            ", ".join(present) or "none",
            ", ".join(missing) or "none",
        ),
    ))
    return checks


def _collect_doctor(export_arg):
    """Return (checks, categories) where checks is a list of (name, status, detail, category)."""

    checks = []

    # Python
    version = "{}.{}.{}".format(*sys.version_info[:3])
    py_status = PASS if sys.version_info[:2] >= (3, 9) else WARN
    checks.append(("python", py_status, "{} ({})".format(version, sys.executable), "baseline"))

    # Baseline deps (required for the evidence workflow)
    for module in ("flask", "requests", "numpy"):
        ok, detail = _probe_import(module)
        checks.append((
            module,
            PASS if ok else FAIL,
            ("version " + detail) if (ok and detail) else (detail if not ok else "installed"),
            "baseline",
        ))

    # Optional semantic stack
    for module, dist in (("chromadb", "chromadb"), ("sentence_transformers", "sentence-transformers")):
        ok, detail = _probe_import(module, dist)
        checks.append((
            module,
            INFO,
            ("installed " + detail).strip() if ok else "not installed (optional; semantic/vector only)",
            "optional",
        ))

    # Headless export prerequisites
    ok, detail = _probe_import("pyghidra")
    checks.append((
        "pyghidra",
        INFO if ok else WARN,
        "installed" if ok else "not installed (needed only for headless export)",
        "headless",
    ))

    java, version_line = _detect_java()
    if java is None:
        checks.append(("jdk", WARN, "no java found (JDK 21 needed for headless export)", "headless"))
    else:
        major = _java_major(version_line)
        if major == 21:
            status = PASS
        else:
            status = WARN
        checks.append((
            "jdk",
            status,
            "{} [{}]{}".format(
                version_line or "unknown version",
                java,
                "" if major == 21 else "  (Ghidra needs JDK 21)",
            ),
            "headless",
        ))

    ghidra = os.environ.get("GHIDRA_INSTALL_DIR")
    if ghidra and os.path.isdir(os.path.join(ghidra, "Ghidra")):
        checks.append(("ghidra", PASS, ghidra, "headless"))
    elif ghidra:
        checks.append(("ghidra", WARN, "GHIDRA_INSTALL_DIR set but not a Ghidra install: {}".format(ghidra), "headless"))
    else:
        checks.append(("ghidra", WARN, "GHIDRA_INSTALL_DIR not set (needed only for headless export)", "headless"))

    # Active export
    export_path, source = host_config.resolve_export_source(export_arg)
    for name, status, detail in _export_checks(export_path, source):
        checks.append((name, status, detail, "export"))

    return checks


def doctor(argv=None):
    parser = argparse.ArgumentParser(
        prog="revhub doctor",
        description="Preflight check of the host environment and the active export.",
    )
    parser.add_argument("--export", dest="export_path", default=None, help="Export to inspect (default: the resolved current export).")
    parser.add_argument("--json", action="store_true", help="Emit the checks as JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings too, not just failures.")
    args = parser.parse_args(argv)

    checks = _collect_doctor(args.export_path)

    failures = [c for c in checks if c[1] == FAIL]
    warnings = [c for c in checks if c[1] == WARN]

    if args.json:
        payload = {
            "checks": [
                {"name": n, "status": s, "detail": d, "category": cat}
                for (n, s, d, cat) in checks
            ],
            "failures": len(failures),
            "warnings": len(warnings),
        }
        print(json.dumps(payload, indent=2))
    else:
        order = ["baseline", "optional", "headless", "export"]
        titles = {
            "baseline": "Baseline (required for the evidence workflow)",
            "optional": "Optional semantic/vector stack",
            "headless": "Headless export prerequisites",
            "export": "Active export",
        }
        print("revhub doctor")
        for category in order:
            group = [c for c in checks if c[3] == category]
            if not group:
                continue
            print("\n" + titles[category])
            for name, status, detail, _cat in group:
                print("  [{:<4}] {:<18} {}".format(status, name, detail))
        print("\nSummary: {} failed, {} warning(s).".format(len(failures), len(warnings)))
        if failures:
            print("Fix the FAIL items above (install the baseline: pip install flask requests numpy).")

    if failures:
        return 1
    if args.strict and warnings:
        return 1
    return 0


# --------------------------------------------------------------------------
# use (current-export pointer)
# --------------------------------------------------------------------------

def use(argv=None):
    parser = argparse.ArgumentParser(
        prog="revhub use",
        description="Show, set, or clear the current-export pointer.",
    )
    parser.add_argument("path", nargs="?", help="Export folder to make current. Omit to show the current one.")
    parser.add_argument("--clear", action="store_true", help="Clear the pointer instead of setting it.")
    args = parser.parse_args(argv)

    if args.clear:
        cleared = host_config.clear_current_export()
        print("Cleared the current-export pointer." if cleared else "No current-export pointer was set.")
        return 0

    if args.path:
        resolved = host_config.write_current_export(args.path)
        print("Current export set to: " + resolved)
        if not os.path.isfile(os.path.join(resolved, "manifest.json")):
            print("  note: no manifest.json there yet — the pointer is saved; populate the export later.")
        return 0

    path, source = host_config.resolve_export_source()
    print("Current export: {}  [{}]".format(path, source))
    print("Pointer file:   {}".format(host_config.pointer_file()))
    return 0


# --------------------------------------------------------------------------
# dispatcher
# --------------------------------------------------------------------------

def _first_positional(rest, value_flags):
    """Return the first positional token in ``rest``, or None.

    ``value_flags`` names options that consume the following token, so an
    option's VALUE (e.g. the ``50`` in ``--limit 50``) is not mistaken for a
    positional export path. Handles both ``--opt value`` and ``--opt=value``.
    """

    index = 0
    while index < len(rest):
        token = rest[index]
        if token.startswith("-") and token != "-":
            if "=" not in token and token in value_flags:
                index += 2  # skip the value token
            else:
                index += 1
            continue
        return token
    return None


def _inject_export(rest, value_flags):
    """Prepend the active export path when no positional path was supplied."""

    if _first_positional(rest, value_flags) is None:
        return [host_config.resolve_export_path()] + rest
    return rest


def _delegate(module_name, func_name, rest):
    module = importlib.import_module(module_name)
    return getattr(module, func_name)(rest) or 0


def _delegate_validate(rest):
    # validate_export.main() reads sys.argv directly, so drive it through argv.
    module = importlib.import_module("tools.validate_export")
    saved = sys.argv
    sys.argv = ["validate_export"] + rest
    try:
        return module.main() or 0
    finally:
        sys.argv = saved


HELP = __doc__


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help"):
        print(HELP)
        return 0

    command, rest = argv[0], argv[1:]

    if command == "doctor":
        return doctor(rest)
    if command == "use":
        return use(rest)
    if command == "validate":
        return _delegate_validate(_inject_export(rest, set()))
    if command in DELEGATES:
        module_name, func_name, value_flags = DELEGATES[command]
        if value_flags is not None:
            rest = _inject_export(rest, value_flags)
        return _delegate(module_name, func_name, rest)

    print("Unknown command: {}\n".format(command), file=sys.stderr)
    print(HELP, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
