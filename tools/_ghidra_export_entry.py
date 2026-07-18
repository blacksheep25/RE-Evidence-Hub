"""
Ghidra-side entry point executed by PyGhidra (see tools/headless_export.py).

This runs inside Ghidra's interpreter with `currentProgram` and `monitor`
injected, exactly like a GhidraScript. It is intentionally tiny so the real
work stays in AIExporter. It is not meant to be run directly.

Ghidra 11.3+ removed Jython, so this module runs under CPython 3 via PyGhidra.
It avoids relying on __file__ (not always defined in Ghidra's interpreter) and
instead reads the repository root from the RE_HUB_REPO_ROOT environment variable
set by the host driver.
"""

import os
import sys

_repo = os.environ.get("RE_HUB_REPO_ROOT")

if _repo and _repo not in sys.path:
    sys.path.insert(0, _repo)

from AIExporter import AIExporter

# `currentProgram` and `monitor` are injected by PyGhidra's run_script, the same
# globals a GhidraScript receives.
print("[headless] exporting: " + currentProgram.getName())  # noqa: F821

AIExporter(currentProgram, monitor).run()  # noqa: F821

print("[headless] export finished")
