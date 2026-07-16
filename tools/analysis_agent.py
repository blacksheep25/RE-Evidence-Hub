"""
analysis_agent.py

Automated first-pass binary analysis.

Consumes:

- imports.json
- strings.json
- function_summaries.json
- callgraph.json

Produces:

- analysis_report.json
- analysis_report.md
"""


import os
import json
import datetime



class AnalysisAgent(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.data = {}



        self.load()



    # --------------------------------------------------------
    # Load files
    # --------------------------------------------------------

    def load(self):


        files = {


            "imports":

                "imports.json",


            "strings":

                "strings.json",


            "summaries":

                "function_summaries.json",


            "callgraph":

                "callgraph.json"

        }



        for key, filename in files.items():


            path = os.path.join(

                self.export_path,

                filename

            )


            if os.path.exists(path):


                with open(

                    path,

                    "r",

                    encoding="utf-8"

                ) as f:


                    self.data[key] = json.load(f)


            else:


                self.data[key] = []



    # --------------------------------------------------------
    # Run analysis
    # --------------------------------------------------------

    def analyze(self):


        report = {


            "created":

                str(
                    datetime.datetime.now()
                ),


            "subsystems":

                [],


            "interesting_functions":

                [],


            "statistics":

                {}

        }



        report["statistics"] = {

            "imports":

                len(
                    self.data["imports"]
                ),


            "functions":

                len(
                    self.data["summaries"]
                )

        }



        report["subsystems"].extend(

            self.detect_subsystems()

        )


        report["interesting_functions"].extend(

            self.rank_functions()

        )



        self.write_report(

            report

        )



    # --------------------------------------------------------
    # Detect subsystems
    # --------------------------------------------------------

    def detect_subsystems(self):


        subsystems = []



        checks = {


            "Networking":

            [

                "socket",

                "connect",

                "recv",

                "send",

                "http"

            ],



            "Filesystem":

            [

                "createfile",

                "readfile",

                "writefile",

                "openfile"

            ],



            "Cryptography":

            [

                "crypt",

                "sha",

                "aes",

                "rsa",

                "hash"

            ],



            "Process":

            [

                "createprocess",

                "shellexecute",

                "thread",

                "service"

            ]

        }



        imports = " ".join(

            str(x)

            for x in self.data["imports"]

        ).lower()



        for name, keywords in checks.items():


            evidence = []


            for keyword in keywords:


                if keyword in imports:


                    evidence.append(

                        keyword

                    )



            if evidence:


                subsystems.append({

                    "name":

                        name,


                    "evidence":

                        evidence

                })



        return subsystems



    # --------------------------------------------------------
    # Rank important functions
    # --------------------------------------------------------

    def rank_functions(self):


        results = []



        keywords = [

            "network",

            "file",

            "crypto",

            "memory"

        ]



        for function in self.data["summaries"]:


            score = 0



            text = str(function).lower()



            for word in keywords:


                if word in text:

                    score += 1



            if score:


                results.append({

                    "function":

                        function.get("name"),


                    "address":

                        function.get("address"),


                    "score":

                        score,


                    "summary":

                        function.get("summary")

                })



        results.sort(

            key=lambda x:

                x["score"],

            reverse=True

        )


        return results[:100]



    # --------------------------------------------------------
    # Write reports
    # --------------------------------------------------------

    def write_report(
            self,
            report):


        json_path = os.path.join(

            self.export_path,

            "analysis_report.json"

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

            "analysis_report.md"

        )


        with open(

            md_path,

            "w",

            encoding="utf-8"

        ) as f:


            f.write(

                "# Binary Analysis Report\n\n"

            )


            f.write(

                "Generated: {}\n\n".format(

                    report["created"]

                )

            )



            f.write(

                "## Subsystems\n\n"

            )


            for subsystem in report["subsystems"]:


                f.write(

                    "- {}: {}\n".format(

                        subsystem["name"],

                        ", ".join(

                            subsystem["evidence"]

                        )

                    )

                )



            f.write(

                "\n## Interesting Functions\n\n"

            )



            for function in report["interesting_functions"]:


                f.write(

                    "- {} ({}) - {}\n".format(

                        function["name"],

                        function["address"],

                        function["summary"]

                    )

                )


        print(

            "[+] Analysis report created"

        )





if __name__ == "__main__":


    import sys


    if len(sys.argv) != 2:


        print(

            "Usage: analysis_agent.py <export folder>"

        )


        sys.exit(1)



    agent = AnalysisAgent(

        sys.argv[1]

    )


    agent.analyze()
