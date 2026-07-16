"""
Shared host-side settings.

These values apply only to normal Python tools, not the Ghidra Script Manager
exporter. Environment variables take precedence so a dataset can be selected
without editing source files.
"""


import os


DEFAULT_EXPORT_PATH = os.environ.get(
    "GHIDRA_AI_EXPORT_PATH",
    os.path.expanduser(
        "~/ghidra_ai_exports/sample_program.exe"
    )
)


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
