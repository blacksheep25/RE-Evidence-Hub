"""Build an optional SQLite FTS index for a portable Ghidra export.

The index is derived data.  It can be deleted and rebuilt at any time without
changing raw function JSON, annotations, or the Ghidra project.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time


INDEX_NAME = "local_evidence.sqlite3"


def load_json(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def build(export_path, output_path=None):
    export_path = os.path.abspath(export_path)
    index = load_json(os.path.join(export_path, "index.json"))
    functions = index.get("functions", {})
    if not functions:
        raise ValueError("index.json has no functions")

    output_path = output_path or os.path.join(export_path, INDEX_NAME)
    temporary_path = output_path + ".tmp"
    if os.path.exists(temporary_path):
        os.remove(temporary_path)

    started = time.perf_counter()
    connection = sqlite3.connect(temporary_path)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            "CREATE VIRTUAL TABLE function_fts USING fts5("
            "address UNINDEXED, raw_name, namespace, signature, body, tokenize='unicode61')"
        )
        connection.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("schema_version", "1"))
        connection.execute("INSERT INTO metadata(key, value) VALUES (?, ?)", ("function_count", str(len(functions))))

        rows = []
        for count, (address, entry) in enumerate(sorted(functions.items()), 1):
            relative_path = entry.get("file", "functions/{}.json".format(address))
            function = load_json(os.path.join(export_path, relative_path))
            decompiler = function.get("decompiler", {})
            body = decompiler.get("c_code", "") if isinstance(decompiler, dict) else ""
            rows.append((
                address,
                function.get("name", entry.get("name", "")),
                function.get("namespace", ""),
                function.get("signature", ""),
                body,
            ))
            if len(rows) >= 500:
                connection.executemany("INSERT INTO function_fts VALUES (?, ?, ?, ?, ?)", rows)
                rows = []
            if count % 5000 == 0:
                print("[+] Indexed {}/{} functions".format(count, len(functions)))
        if rows:
            connection.executemany("INSERT INTO function_fts VALUES (?, ?, ?, ?, ?)", rows)
        connection.commit()
    finally:
        connection.close()

    os.replace(temporary_path, output_path)
    elapsed = time.perf_counter() - started
    print("Built {} in {:.1f}s ({} functions).".format(output_path, elapsed, len(functions)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the optional local SQLite FTS index for a Ghidra export.")
    parser.add_argument("export_path")
    parser.add_argument("--output", help="Derived SQLite path; defaults to <export>/local_evidence.sqlite3")
    args = parser.parse_args(argv)
    try:
        build(args.export_path, args.output)
        return 0
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as error:
        print("[ERROR] {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
