"""
validate_export.py

Validate the structural contract of a Ghidra AI export.

Usage:
    python tools/validate_export.py <export-folder> [--full]
"""


import json
import os
import sys


REQUIRED_FILES = [
    "manifest.json",
    "imports.json",
    "strings.json",
    "globals.json",
    "callgraph.json",
    "index.json"
]


FUNCTION_FIELDS = [
    "address",
    "name",
    "signature",
    "assembly",
    "calls",
    "called_by",
    "decompiler"
]


def load_json(path):


    with open(
        path,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as file:


        return json.load(file)


def main():


    if len(sys.argv) not in (2, 3):


        print(
            "Usage: python tools/validate_export.py <export-folder> [--full]"
        )


        return 1


    export_path = os.path.abspath(sys.argv[1])
    full_check = len(sys.argv) == 3 and sys.argv[2] == "--full"


    if not os.path.isdir(export_path):


        print("[ERROR] Export folder not found: {}".format(export_path))


        return 1


    errors = []
    warnings = []


    for name in REQUIRED_FILES:


        path = os.path.join(export_path, name)


        if not os.path.isfile(path):


            errors.append("Missing required file: {}".format(name))


    if errors:


        for message in errors:


            print("[ERROR] {}".format(message))


        return 1


    try:


        manifest = load_json(
            os.path.join(export_path, "manifest.json")
        )
        index = load_json(
            os.path.join(export_path, "index.json")
        )


    except (IOError, ValueError) as error:


        print("[ERROR] Invalid JSON: {}".format(error))


        return 1


    function_dir = os.path.join(export_path, "functions")


    if not os.path.isdir(function_dir):


        print("[ERROR] Missing functions directory")


        return 1


    filenames = sorted(
        name for name in os.listdir(function_dir)
        if name.endswith(".json")
    )


    indexed_functions = index.get("functions", {})


    expected_count = manifest.get(
        "functions",
        {}
    ).get("count")


    print("Functions on disk: {}".format(len(filenames)))
    print("Functions indexed: {}".format(len(indexed_functions)))


    if expected_count is not None and expected_count != len(filenames):


        errors.append(
            "Manifest declares {} functions, but {} files exist".format(
                expected_count,
                len(filenames)
            )
        )


    for address, entry in indexed_functions.items():


        if entry.get("address") != address:


            errors.append(
                "Index key is not its function address: {}".format(address)
            )


        relative_path = entry.get("file", "")


        if not relative_path or not os.path.isfile(
            os.path.join(export_path, relative_path)
        ):


            errors.append(
                "Index entry points to a missing function file: {}".format(
                    address
                )
            )


    if len(indexed_functions) != len(filenames):


        warnings.append(
            "Index/function count differs; rebuild index.json before using search"
        )


    check_files = filenames if full_check else filenames[:100]


    for filename in check_files:


        path = os.path.join(function_dir, filename)


        try:


            function = load_json(path)


        except (IOError, ValueError) as error:


            errors.append("Invalid function JSON {}: {}".format(filename, error))
            continue


        for field in FUNCTION_FIELDS:


            if field not in function:


                errors.append(
                    "{} is missing '{}'".format(filename, field))


        if function.get("address") != filename[:-5]:


            errors.append(
                "Function filename/address mismatch: {}".format(filename))


    print(
        "Function files checked: {}{}".format(
            len(check_files),
            " (full)" if full_check else " (first 100; use --full for all)"
        )
    )


    for message in warnings:


        print("[WARN] {}".format(message))


    for message in errors:


        print("[ERROR] {}".format(message))


    if errors:


        print("Validation failed: {} error(s)".format(len(errors)))
        return 1


    print("Validation passed")
    return 0


if __name__ == "__main__":


    sys.exit(main())
