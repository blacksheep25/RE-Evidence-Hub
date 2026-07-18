"""
callgraph_agent.py

Analyzes function relationships.

Uses:

- callgraph.json

Produces:

- important functions
- call paths
- graph statistics
- markdown report
"""


import os
import json
import datetime



class CallgraphAgent(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path

        self.graph = {}

        self.reverse_graph = {}

        self.load()



    # --------------------------------------------------------
    # Load graph
    # --------------------------------------------------------

    def load(self):


        path = os.path.join(

            self.export_path,

            "callgraph.json"

        )


        if not os.path.exists(path):

            raise RuntimeError(

                "callgraph.json missing"

            )


        with open(

            path,

            "r",

            encoding="utf-8"

        ) as f:


            self.graph = json.load(f)



        self.build_reverse_graph()



    # --------------------------------------------------------
    # Reverse edges
    # --------------------------------------------------------

    def build_reverse_graph(self):


        for function, calls in self.graph.items():


            if function not in self.reverse_graph:

                self.reverse_graph[function] = []



            for target in calls:


                if target not in self.reverse_graph:

                    self.reverse_graph[target] = []



                self.reverse_graph[target].append(

                    function

                )



    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    def statistics(self):


        results = []


        for function, calls in self.graph.items():


            results.append({

                "function":

                    function,


                "calls":

                    len(calls),


                "callers":

                    len(

                        self.reverse_graph.get(

                            function,

                            []

                        )

                    )

            })



        results.sort(

            key=lambda x:

                (

                    x["calls"]

                    +

                    x["callers"]

                ),

            reverse=True

        )


        return results



    # --------------------------------------------------------
    # Find path
    # --------------------------------------------------------

    def find_path(
            self,
            start,
            target,
            visited=None):


        if visited is None:

            visited = set()



        if start in visited:

            return None



        visited.add(start)



        if start == target:

            return [

                start

            ]



        for child in self.graph.get(

            start,

            []

        ):


            path = self.find_path(

                child,

                target,

                visited

            )



            if path:


                return [

                    start

                ] + path



        return None



    # --------------------------------------------------------
    # Generate report
    # --------------------------------------------------------

    def analyze(self):


        report = {


            "created":

                str(

                    datetime.datetime.now()

                ),


            "functions":

                len(

                    self.graph

                ),


            "most_connected":

                self.statistics()[:100]

        }



        self.write(report)



    # --------------------------------------------------------
    # Write files
    # --------------------------------------------------------

    def write(
            self,
            report):


        json_file = os.path.join(

            self.export_path,

            "callgraph_analysis.json"

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

            "callgraph_analysis.md"

        )


        with open(

            md_file,

            "w",

            encoding="utf-8"

        ) as f:


            f.write(

                "# Callgraph Analysis\n\n"

            )


            f.write(

                "Functions: {}\n\n".format(

                    report["functions"]

                )

            )


            f.write(

                "## Most Connected Functions\n\n"

            )


            for item in report["most_connected"]:


                f.write(

                    "- {} | calls={} | callers={}\n".format(

                        item["function"],

                        item["calls"],

                        item["callers"]

                    )

                )



        print(

            "[+] Callgraph analysis complete"

        )





if __name__ == "__main__":


    import sys


    if len(sys.argv) != 2:


        print(

            "Usage: callgraph_agent.py <export folder>"

        )


        sys.exit(1)



    agent = CallgraphAgent(

        sys.argv[1]

    )


    agent.analyze()
