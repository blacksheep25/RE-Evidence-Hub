"""Shared, dependency-free project/export layout helpers.

This module is imported both by normal CPython tools and by the PyGhidra
exporter.  Keep it standard-library-only and conservative in syntax.
"""

import os
import re


REPOSITORY_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS_ROOT_ENV = "RE_EVIDENCE_PROJECTS_ROOT"


def projects_root():
    """Return the configured root containing one directory per RE project."""

    configured = os.environ.get(PROJECTS_ROOT_ENV)
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    return os.path.join(REPOSITORY_ROOT, "project_exports")


def safe_project_name(value):
    """Return a filesystem-safe, stable project name without hiding identity."""

    name = os.path.basename(str(value or "").strip())
    name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", name)
    name = re.sub(r"\s+", "_", name).strip(" ._")
    return name or "unnamed_project"


def project_export_path(value, root=None):
    """Return the export directory for a program/project name."""

    return os.path.join(root or projects_root(), safe_project_name(value))


def resolve_project_or_path(value):
    """Resolve an existing/explicit path, otherwise a project name under root."""

    requested = os.path.expanduser(str(value or "").strip())
    if not requested:
        return requested
    if os.path.isabs(requested) or os.path.dirname(requested):
        return os.path.abspath(requested)
    candidate = project_export_path(requested)
    if os.path.isdir(candidate) or not os.path.exists(requested):
        return os.path.abspath(candidate)
    return os.path.abspath(requested)


def discover_projects(root=None):
    """List directories with a manifest, ignoring partial/in-progress exports."""

    base = os.path.abspath(root or projects_root())
    if not os.path.isdir(base):
        return []
    projects = []
    for name in sorted(os.listdir(base), key=str.lower):
        path = os.path.join(base, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "manifest.json")):
            projects.append({"name": name, "path": path})
    return projects
