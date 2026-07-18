"""
Shared host-side settings.

These values apply only to normal Python tools, not the Ghidra Script Manager
exporter. Environment variables take precedence so a dataset can be selected
without editing source files.

The active export is resolved with this precedence (first match wins):

1. An explicit path passed on the command line (``--export`` / positional).
2. The ``GHIDRA_AI_EXPORT_PATH`` environment variable (a per-session override).
3. The saved "current export" pointer written by ``revhub use <export>``.
4. The repo-local default (``project_exports/sample_program.exe``).

Tools that default ``--export`` to :data:`DEFAULT_EXPORT_PATH` therefore pick up
the pointer automatically, while an explicit path always wins.
"""


import os

from project_layout import project_export_path, resolve_project_or_path


_BUILTIN_DEFAULT_EXPORT_PATH = project_export_path("sample_program.exe")


def _config_dir():
    """User config directory for revhub, platform-appropriate."""

    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")

    return os.path.join(base, "re-evidence-hub")


def pointer_file():
    """Path of the file that stores the current-export pointer."""

    return os.path.join(_config_dir(), "current_export")


def read_current_export():
    """Return the saved current-export path, or None if unset/empty."""

    try:
        with open(pointer_file(), "r", encoding="utf-8") as handle:
            value = handle.read().strip()
    except OSError:
        return None

    return value or None


def write_current_export(path):
    """Persist an absolute current-export pointer and return it."""

    resolved = resolve_project_or_path(path)

    os.makedirs(_config_dir(), exist_ok=True)

    with open(pointer_file(), "w", encoding="utf-8") as handle:
        handle.write(resolved)

    return resolved


def clear_current_export():
    """Remove the current-export pointer. Returns True if one existed."""

    try:
        os.remove(pointer_file())
        return True
    except OSError:
        return False


def resolve_export_source(explicit=None):
    """Resolve the active export as ``(path, source)`` by precedence."""

    if explicit:
        return explicit, "argument"

    env = os.environ.get("GHIDRA_AI_EXPORT_PATH")
    if env:
        return env, "GHIDRA_AI_EXPORT_PATH env"

    pointer = read_current_export()
    if pointer:
        return pointer, "current-export pointer"

    return _BUILTIN_DEFAULT_EXPORT_PATH, "built-in default"


def resolve_export_path(explicit=None):
    """Resolve the active export path by precedence (see module docstring)."""

    return resolve_export_source(explicit)[0]


DEFAULT_EXPORT_PATH = resolve_export_path()


DEFAULT_RESOURCE_ROOT = os.environ.get("GHIDRA_AI_RESOURCE_ROOT", "")


DEFAULT_CHROMA_PATH = os.environ.get(
    "GHIDRA_AI_CHROMA_PATH",
    os.path.expanduser(
        "~/ghidra_ai_chroma"
    )
)


CHROMA_COLLECTION = os.environ.get(
    "GHIDRA_AI_CHROMA_COLLECTION",
    "ghidra"
)


EMBEDDING_MODEL = os.environ.get(
    "GHIDRA_AI_EMBEDDING_MODEL",
    "BAAI/bge-base-en-v1.5"
)


API_PORT = int(
    os.environ.get(
        "GHIDRA_AI_API_PORT",
        "5006"
    )
)
