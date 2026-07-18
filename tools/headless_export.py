#!/usr/bin/env python3
"""
Headless export driver for the Ghidra AI Exporter.

Ghidra 11.3+ removed Jython, so `.py` GhidraScripts run through PyGhidra
(CPython 3 + JPype). This script imports a binary, runs auto-analysis, and runs
the exporter pipeline without opening the Ghidra GUI.

Prerequisites:
  - A local Ghidra install (>= 12.0). Point to it with --ghidra or the
    GHIDRA_INSTALL_DIR environment variable.
  - A JDK 21 (Ghidra's requirement). Found via --java-home, JAVA_HOME, PATH, or
    a Temurin / Microsoft OpenJDK install under "Program Files".
  - PyGhidra installed in this Python environment:
      pip install --no-index -f <GHIDRA>/Ghidra/Features/PyGhidra/pypkg/dist pyghidra
    (or `pip install pyghidra` with network access)

Example:
  python tools/headless_export.py --binary "C:/samples/DownloadServer.exe"

The export is written to ~/ghidra_ai_exports/<ProgramName>/ (the exporter's
configured output root; see config.py). Validate it afterwards with
tools/validate_export.py.
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys
import tempfile
import warnings


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY_SCRIPT = os.path.join(REPO_ROOT, "tools", "_ghidra_export_entry.py")


def find_ghidra(explicit):
    """Return a validated Ghidra install dir, or None to defer to PyGhidra."""
    candidate = explicit or os.environ.get("GHIDRA_INSTALL_DIR")
    if not candidate:
        return None
    candidate = os.path.abspath(os.path.expanduser(candidate))
    if os.path.isdir(os.path.join(candidate, "Ghidra")):
        return candidate
    return None


def _is_jdk(path):
    if not path:
        return False
    bin_dir = os.path.join(path, "bin")
    return os.path.isfile(os.path.join(bin_dir, "java.exe")) or \
        os.path.isfile(os.path.join(bin_dir, "java"))


def find_java_home(explicit):
    """Return a JDK home to export, or None if java is already resolvable."""
    for value in (explicit, os.environ.get("JAVA_HOME")):
        if _is_jdk(value):
            return value
    for base in (
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
    ):
        for match in sorted(glob.glob(os.path.join(base, "jdk-21*")), reverse=True):
            if _is_jdk(match):
                return match
    return None


def expected_output(program_name):
    root = os.path.expanduser("~/ghidra_ai_exports")
    return os.path.join(root, program_name.replace(" ", "_"))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Headless Ghidra AI export via PyGhidra (no Ghidra GUI).",
    )
    parser.add_argument("--binary", required=True, help="Path to the binary to export.")
    parser.add_argument("--ghidra", help="Ghidra install dir (default: $GHIDRA_INSTALL_DIR).")
    parser.add_argument("--java-home", help="JDK 21 home (default: $JAVA_HOME / PATH / Temurin).")
    parser.add_argument("--project-dir", help="Where to create the temporary Ghidra project (default: a temp dir).")
    parser.add_argument("--keep-project", action="store_true", help="Keep the temporary Ghidra project instead of deleting it.")
    parser.add_argument("--no-analyze", action="store_true", help="Skip auto-analysis (only if the program is already analyzed).")
    args = parser.parse_args(argv)

    binary = os.path.abspath(os.path.expanduser(args.binary))
    if not os.path.isfile(binary):
        parser.error("Binary not found: " + binary)

    ghidra = find_ghidra(args.ghidra)
    if ghidra:
        os.environ["GHIDRA_INSTALL_DIR"] = ghidra
        dist_hint = os.path.join(ghidra, "Ghidra", "Features", "PyGhidra", "pypkg", "dist")
    else:
        print("[headless] warning: Ghidra install dir not set; relying on PyGhidra 'lastrun'.")
        print("[headless] pass --ghidra or set GHIDRA_INSTALL_DIR if startup fails.")
        dist_hint = "<GHIDRA>/Ghidra/Features/PyGhidra/pypkg/dist"

    java_home = find_java_home(args.java_home)
    if java_home:
        os.environ["JAVA_HOME"] = java_home
        print("[headless] JAVA_HOME=" + java_home)
    elif not shutil.which("java"):
        parser.error("No JDK found. Install JDK 21 and set --java-home or JAVA_HOME.")

    # The exporter derives its output folder from the loaded program's name,
    # which for a file import is the binary's filename. Ghidra project naming
    # does not change that, so the export subfolder always matches the binary.
    program_name = os.path.basename(binary)

    # Make the repo importable from the PyGhidra-run entry script (same process).
    os.environ["RE_HUB_REPO_ROOT"] = REPO_ROOT
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)

    try:
        import pyghidra
    except ImportError:
        sys.exit(
            "PyGhidra is not installed in this environment.\n"
            "Install it (offline) with:\n"
            '  pip install --no-index -f "%s" pyghidra\n'
            "or with network access:  pip install pyghidra" % dist_hint
        )

    project_dir = args.project_dir
    cleanup = False
    if not project_dir:
        project_dir = tempfile.mkdtemp(prefix="ghidra_headless_")
        cleanup = not args.keep_project

    print("[headless] binary : " + binary)
    print("[headless] project: " + project_dir)
    print("[headless] program: " + program_name)

    try:
        # run_script is marked legacy in PyGhidra 3.x but remains supported and
        # is by far the simplest one-call import+analyze+run. The successor is
        # open_project() + program_loader() + ghidra_script(); switch to it if a
        # future PyGhidra drops run_script. The deprecation notice is filtered so
        # tool output stays clean.
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="pyghidra")
        pyghidra.run_script(
            binary,
            ENTRY_SCRIPT,
            project_location=project_dir,
            project_name=os.path.splitext(program_name)[0],
            analyze=not args.no_analyze,
            verbose=False,
        )
    finally:
        if cleanup:
            shutil.rmtree(project_dir, ignore_errors=True)

    out = expected_output(program_name)
    print("")
    print("[headless] export complete -> " + out)
    print("[headless] validate with:")
    print('  python tools/validate_export.py "%s" --full' % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
