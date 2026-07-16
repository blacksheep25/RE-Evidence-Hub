"""
binary_triage.py

Automatic first-pass binary analysis.

Reads:

- manifest.json
- imports.json
- strings.json
- functions/*.json
- evidence_database.json

Produces:

- triage_report.json
- triage_report.md

Purpose:

Create an initial investigation map.
"""


import os
import json
import datetime



class BinaryTriage:


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.manifest = {}

        self.imports = []

        self.strings = []

        self.functions = []

        self.evidence = []



        self.load()



    # -------------------------------------------------
    # Load exported information
    # -------------------------------------------------

    def load(self):


        def read_json(name):

            path = os.path.join(

                self.export_path,

                name

            )


            if os.path.exists(path):

                with open(

                    path,

                    "r",

                    encoding="utf-8"

                ) as f:

                    return json.load(f)


            return {}



        self.manifest = read_json(

            "manifest.json"

        )


        self.imports = read_json(

            "imports.json"

        )


        self.strings = read_json(

            "strings.json"

        )


        evidence = read_json(

            "evidence_database.json"

        )


        self.evidence = evidence.get(

            "functions",

            []

        )



        function_dir = os.path.join(

            self.export_path,

            "functions"

        )


        if os.path.exists(function_dir):


            for file in os.listdir(function_dir):


                if file.endswith(".json"):


                    with open(

                        os.path.join(

                            function_dir,

                            file

                        ),

                        "r",

                        encoding="utf-8"

                    ) as f:


                        self.functions.append(

                            json.load(f)

                        )



    # -------------------------------------------------
    # Search indicators
    # -------------------------------------------------

    def indicator_search(
            self,
            keywords,
            data):


        hits = []


        text = json.dumps(

            data

        ).lower()



        for keyword in keywords:


            if keyword.lower() in text:


                hits.append(

                    keyword

                )


        return hits



    # -------------------------------------------------
    # Detect subsystems
    # -------------------------------------------------

    def detect_subsystems(self):


        results = []



        categories = {


            "networking":

            [

                "socket",

                "connect",

                "recv",

                "send",

                "http",

                "tcp"

            ],



            "authentication":

            [

                "login",

                "password",

                "username",

                "token",

                "credential"

            ],



            "cryptography":

            [

                "encrypt",

                "decrypt",

                "sha",

                "aes",

                "rsa",

                "hash"

            ],



            "filesystem":

            [

                "file",

                "open",

                "read",

                "write"

            ]

        }



        for name, keywords in categories.items():


            hits = self.indicator_search(

                keywords,

                self.functions

            )


            if hits:


                results.append({

                    "subsystem":

                        name,


                    "indicators":

                        hits

                })


        return results



    # -------------------------------------------------
    # Rank functions
    # -------------------------------------------------

    def rank_functions(self):


        ranked = []


        for item in self.evidence:


            score = item.get(

                "confidence",

                0

            )


            ranked.append({

                "name":

                    item.get(

                        "name"

                    ),


                "address":

                    item.get(

                        "address"

                    ),


                "score":

                    score,


                "signals":

                    item.get(

                        "signals",

                    )

            })



        ranked.sort(

            key=lambda x:

                x["score"],

            reverse=True

        )


        return ranked[:25]



    # -------------------------------------------------
    # Generate
    # -------------------------------------------------

    def generate(self):


        report = {


            "created":

                str(

                    datetime.datetime.now()

                ),


            "binary":

                self.manifest.get(

                    "binary",

                    {}

                ),


            "subsystems":

                self.detect_subsystems(),


            "priority_functions":

                self.rank_functions(),


            "recommended_tasks":

            [

                "Analyze entry point",

                "Trace networking",

                "Inspect authentication",

                "Identify encryption usage",

                "Review high confidence functions"

            ]

        }



        self.write(report)



    # -------------------------------------------------
    # Write files
    # -------------------------------------------------

    def write(
            self,
            report):


        json_path = os.path.join(

            self.export_path,

            "triage_report.json"

        )


        with open(

            json_path,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                report,

                f,

                indent=2

            )



        md_path = os.path.join(

            self.export_path,

            "triage_report.md"

        )


        with open(

            md_path,

            "w",

            encoding="utf-8"

        ) as f:


            f.write(

                "# Binary Triage Report\n\n"

            )


            binary = report["binary"]


            f.write(

                "Binary: {}\n\n".format(

                    binary.get(

                        "name",

                        "unknown"

                    )

                )

            )



            f.write(

                "## Detected Subsystems\n\n"

            )


            for item in report["subsystems"]:


                f.write(

                    "- {}\n".format(

                        item["subsystem"]

                    )

                )


                for signal in item["indicators"]:


                    f.write(

                        "  - {}\n".format(

                            signal

                        )

                    )



            f.write(

                "\n## Priority Functions\n\n"

            )


            for function in report["priority_functions"]:


                f.write(

                    "- {} @ {} (score {})\n".format(

                        function["name"],

                        function["address"],

                        function["score"]

                    )

                )



        print(

            "[+] Binary triage complete"

        )





if __name__ == "__main__":


    import sys


    if len(sys.argv) != 2:


        print(

            "Usage: python binary_triage.py <export folder>"

        )

        sys.exit(1)



    BinaryTriage(

        sys.argv[1]

    ).generate()
