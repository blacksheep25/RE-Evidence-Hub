#!/usr/bin/env python3
"""Fail CI when tracked content is unsafe for a public source repository."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Iterable, List


ALLOWED_PROJECT_EXPORT_FILES = {"project_exports/.gitignore", "project_exports/README.md"}
BLOCKED_PREFIXES = ("project_exports/", "RE Work/")
BLOCKED_SUFFIXES = (
    ".exe", ".dll", ".bin", ".sqlite", ".sqlite3", ".zip", ".7z", ".rar", ".tar", ".gz", ".dmp", ".pdb", ".idb",
)
SECRET_PATTERNS = (
    re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def tracked_files() -> List[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"])
    return [item.replace("\\", "/") for item in output.decode("utf-8").split("\0") if item]


def path_finding(path: str) -> str:
    if path in ALLOWED_PROJECT_EXPORT_FILES:
        return ""
    if path.startswith(BLOCKED_PREFIXES):
        return "tracked target/export path"
    if path.lower().endswith(BLOCKED_SUFFIXES):
        return "tracked binary, database, archive, or debug artifact"
    return ""


def content_findings(data: bytes) -> Iterable[str]:
    if b"\0" in data:
        return []
    text = data.decode("utf-8", errors="replace")
    return ["possible secret" for pattern in SECRET_PATTERNS if pattern.search(text)]


def findings(paths: Iterable[str], root: str = ".") -> List[str]:
    result = []
    for path in paths:
        reason = path_finding(path)
        if reason:
            result.append("{}: {}".format(path, reason))
            continue
        full_path = os.path.join(root, path)
        try:
            with open(full_path, "rb") as handle:
                data = handle.read()
        except OSError as exc:
            result.append("{}: unable to scan ({})".format(path, exc))
            continue
        result.extend("{}: {}".format(path, item) for item in content_findings(data))
    return result


def main() -> int:
    problems = findings(tracked_files())
    if problems:
        print("Public release check failed:", file=sys.stderr)
        print("\n".join("- " + problem for problem in problems), file=sys.stderr)
        return 1
    print("Public release check passed: no blocked tracked artifacts or obvious secrets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
