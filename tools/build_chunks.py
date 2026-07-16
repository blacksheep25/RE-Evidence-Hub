"""
build_chunks.py

Create ai_chunks.json from an existing Ghidra export without rerunning Ghidra.

Usage:
    python tools/build_chunks.py <export-folder>
"""


import os
import sys


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


if PROJECT_ROOT not in sys.path:

    sys.path.insert(
        0,
        PROJECT_ROOT
    )


from exporters.embedding_exporter import EmbeddingExporter


def main():


    if len(sys.argv) != 2:


        print(
            "Usage: python tools/build_chunks.py <export-folder>"
        )


        return 1


    exporter = EmbeddingExporter(
        program=None,
        monitor=None,
        output=sys.argv[1],
        config=None
    )


    exporter.export()


    return 0


if __name__ == "__main__":


    sys.exit(main())
