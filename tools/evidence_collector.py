"""
Build a compact, evidence-backed record for each exported function.

The collector deliberately uses the caller/function references already emitted
by the Ghidra exporters. It does not scan every import and string against every
function's serialised JSON; that approach becomes impractical for large client
exports such as the target application.
"""


import datetime
import json
import os
import sys


MARKERS = {
    "network": ["recv", "send", "connect", "socket"],
    "crypto": ["hash", "encrypt", "decrypt", "sha"],
    "memory": ["malloc", "free", "alloc"]
}


class EvidenceCollector(object):


    def __init__(self, export_path):


        self.export_path = export_path
        self.function_directory = os.path.join(export_path, "functions")
        self.imports_by_function = {}
        self.strings_by_function = {}


        self.load()


    @staticmethod
    def load_json(path):


        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as file:


            return json.load(file)


    @staticmethod
    def append_index(index, address, item):


        if not address:


            return


        if address not in index:


            index[address] = []


        index[address].append(item)


    def load(self):


        imports_path = os.path.join(self.export_path, "imports.json")
        strings_path = os.path.join(self.export_path, "strings.json")


        if os.path.isfile(imports_path):


            for imported_api in self.load_json(imports_path):


                evidence = {
                    "name": imported_api.get("name", ""),
                    "library": imported_api.get("library", ""),
                    "address": imported_api.get("address", "")
                }


                for caller in imported_api.get("references", []):


                    self.append_index(
                        self.imports_by_function,
                        caller.get("address"),
                        evidence
                    )


        if os.path.isfile(strings_path):


            for string in self.load_json(strings_path):


                evidence = {
                    "address": string.get("address", ""),
                    "value": string.get("value", "")
                }


                for function in string.get("functions", []):


                    self.append_index(
                        self.strings_by_function,
                        function.get("address"),
                        evidence
                    )


    def collect(self):


        if not os.path.isdir(self.function_directory):


            raise RuntimeError("functions directory missing")


        filenames = sorted(
            filename
            for filename in os.listdir(self.function_directory)
            if filename.endswith(".json")
        )


        database = {
            "version": "2.0",
            "created": str(datetime.datetime.now()),
            "functions": []
        }


        for count, filename in enumerate(filenames, 1):


            function = self.load_json(
                os.path.join(self.function_directory, filename)
            )


            database["functions"].append(
                self.analyze_function(function)
            )


            if count % 1000 == 0:


                print(
                    "[+] Evidence: {}/{}".format(
                        count,
                        len(filenames)
                    )
                )


        self.save(database)


    def analyze_function(self, function):


        address = function.get("address", "")
        imports = self.imports_by_function.get(address, [])
        strings = self.strings_by_function.get(address, [])


        evidence = {
            "address": address,
            "name": function.get("name", ""),
            "signals": [],
            "references": {
                "calls": function.get("calls", []),
                "called_by": function.get("called_by", [])
            },
            "confidence": 0
        }


        if imports:


            evidence["signals"].append({
                "type": "imports",
                "data": imports[:20]
            })
            evidence["confidence"] += 1


        if strings:


            evidence["signals"].append({
                "type": "strings",
                "data": strings[:20]
            })
            evidence["confidence"] += 1


        text = self.function_text(function)


        for category, words in MARKERS.items():


            hits = [word for word in words if word in text]


            if hits:


                evidence["signals"].append({
                    "type": category,
                    "data": hits
                })
                evidence["confidence"] += 1


        return evidence


    @staticmethod
    def function_text(function):


        decompiler = function.get("decompiler", {})


        if not isinstance(decompiler, dict):


            decompiler = {}


        call_names = []


        for call in function.get("calls", []):


            if isinstance(call, dict):


                call_names.append(call.get("name", ""))


        return " ".join([
            function.get("name", ""),
            function.get("signature", ""),
            " ".join(call_names),
            decompiler.get("c_code", ""),
            function.get("assembly", "")
        ]).lower()


    def save(self, database):


        path = os.path.join(
            self.export_path,
            "evidence_database.json"
        )


        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:


            json.dump(database, file, indent=2)


        print(
            "[+] Evidence database created: {} functions".format(
                len(database["functions"])
            )
        )


if __name__ == "__main__":


    if len(sys.argv) != 2:


        print("Usage: python evidence_collector.py <export-folder>")
        sys.exit(1)


    EvidenceCollector(sys.argv[1]).collect()
