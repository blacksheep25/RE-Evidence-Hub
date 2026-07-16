"""
startup_analyzer.py

Attempts to reconstruct program startup flow.

Uses:

- manifest.json
- callgraph.json
- function exports

Produces:

- startup_analysis.json
- startup_analysis.md
"""


import os
import json
import datetime



class StartupAnalyzer(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path

        self.functions = {}

        self.callgraph = {}

        self.manifest = {}

        self.load()



    # --------------------------------------------------------
    # Load exported data
    # --------------------------------------------------------

    def load(self):


        manifest = os.path.join(

            self.export_path,

            "manifest.json"

        )


        if os.path.exists(manifest):


            with open(

                manifest,

                "r",

                encoding="utf-8"

            ) as f:


                self.manifest = json.load(f)



        graph = os.path.join(

            self.export_path,

            "callgraph.json"

        )


        if os.path.exists(graph):


            with open(

                graph,

                "r",

                encoding="utf-8"

            ) as f:


                self.callgraph = json.load(f)



        function_dir = os.path.join(

            self.export_path,

            "functions"

        )


        if os.path.exists(function_dir):


            for filename in os.listdir(function_dir):


                if filename.endswith(".json"):


                    path = os.path.join(

                        function_dir,

                        filename

                    )


                    with open(

                        path,

                        "r",

                        encoding="utf-8"

                    ) as f:


                        data = json.load(f)


                        self.functions[

                            data.get(

                                "address",

                                filename

                            )

                        ] = data



    # --------------------------------------------------------
    # Find probable entry point
    # --------------------------------------------------------

    def find_entry(self):


        candidates = []



        image_base = (

            self.manifest

            .get(

                "binary",

                {}

            )

            .get(

                "image_base",

                ""

            )

        )



        for address, function in self.functions.items():


            name = function.get(

                "name",

                ""

            ).lower()



            score = 0



            if name in [

                "main",

                "entry",

                "_main",

                "winmain"

            ]:

                score += 10



            if address.lower() == image_base.lower():

                score += 5



            if score:


                candidates.append({

                    "address":

                        address,


                    "name":

                        function.get(

                            "name"

                        ),


                    "score":

                        score

                })



        candidates.sort(

            key=lambda x:

                x["score"],

            reverse=True

        )


        if candidates:

            return candidates[0]


        return None



    # --------------------------------------------------------
    # Trace execution
    # --------------------------------------------------------

    def trace(
            self,
            address,
            depth=5):


        chain = []


        current = address



        for _ in range(depth):


            if current in chain:

                break



            chain.append(current)



            children = self.callgraph.get(

                current,

                []

            )



            if not children:

                break



            current = children[0]



        return chain



    # --------------------------------------------------------
    # Generate report
    # --------------------------------------------------------

    def analyze(self):


        entry = self.find_entry()


        report = {


            "created":

                str(

                    datetime.datetime.now()

                ),


            "entry":

                entry,


            "startup_chain":

                []

        }



        if entry:


            report["startup_chain"] = self.trace(

                entry["address"]

            )



        self.write(

            report

        )



    # --------------------------------------------------------
    # Write report
    # --------------------------------------------------------

    def write(
            self,
            report):


        json_file = os.path.join(

            self.export_path,

            "startup_analysis.json"

        )


        with open(

            json_file,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                report,

                f,

                indent=2

            )



        md_file = os.path.join(

            self.export_path,

            "startup_analysis.md"

        )


        with open(

            md_file,

            "w",

            encoding="utf-8"

        ) as f:


            f.write(

                "# Startup Analysis\n\n"

            )


            if report["entry"]:


                f.write(

                    "Entry: {} {}\n\n".format(

                        report["entry"]["name"],

                        report["entry"]["address"]

                    )

                )



            f.write(

                "## Startup Chain\n\n"

            )


            for item in report["startup_chain"]:


                function = self.functions.get(

                    item,

                    {}

                )


                f.write(

                    "- {} ({})\n".format(

                        function.get(

                            "name",

                            "unknown"

                        ),

                        item

                    )

                )



        print(

            "[+] Startup analysis complete"

        )





if __name__ == "__main__":


    import sys


    if len(sys.argv) != 2:


        print(

            "Usage: startup_analyzer.py <export folder>"

        )


        sys.exit(1)



    analyzer = StartupAnalyzer(

        sys.argv[1]

    )


    analyzer.analyze()
