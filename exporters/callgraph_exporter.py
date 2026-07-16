"""
callgraph_exporter.py

Builds a complete program call graph.

Output:

callgraph.json

Contains:

- Nodes
- Edges
- Function relationships
- External calls
"""


import os


from util.jsonwriter import JSONWriter



class CallGraphExporter(object):


    VERSION = "1.0"



    def __init__(
            self,
            program,
            monitor,
            output,
            config):


        self.program = program
        self.monitor = monitor
        self.output = output
        self.config = config


        self.function_manager = (
            program
            .getFunctionManager()
        )


        self.listing = (
            program
            .getListing()
        )


        self.graph = {

            "version":
                self.VERSION,

            "nodes":
                [],

            "edges":
                []

        }



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        print(
            "[+] Building call graph"
        )


        self.build_nodes()

        self.build_edges()


        path = os.path.join(

            self.output,

            "callgraph.json"

        )


        JSONWriter.save(

            path,

            self.graph

        )


        print(
            "[+] Call graph exported"
        )



    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    def build_nodes(self):


        iterator = (
            self.function_manager
            .getFunctions(True)
        )


        while iterator.hasNext():


            function = iterator.next()


            self.graph["nodes"].append({

                "id":
                    str(
                        function
                        .getEntryPoint()
                    ),

                "name":
                    function
                    .getName(),

                "external":
                    function
                    .isExternal(),

                "namespace":
                    str(
                        function
                        .getParentNamespace()
                    )

            })



    # --------------------------------------------------------
    # Edges
    # --------------------------------------------------------

    def build_edges(self):


        iterator = (
            self.function_manager
            .getFunctions(True)
        )


        while iterator.hasNext():


            function = iterator.next()


            source = str(

                function
                .getEntryPoint()

            )


            instructions = (
                self.listing
                .getInstructions(
                    function.getBody(),
                    True
                )
            )


            while instructions.hasNext():


                instruction = (
                    instructions.next()
                )


                flows = (
                    instruction
                    .getFlows()
                )


                for flow in flows:


                    target = (
                        self.function_manager
                        .getFunctionAt(flow)
                    )


                    if target:


                        self.graph["edges"].append({

                            "from":
                                source,

                            "to":
                                str(
                                    target
                                    .getEntryPoint()
                                ),

                            "type":
                                "CALL"

                        })



        self.graph["edges"] = (
            self.unique(
                self.graph["edges"]
            )
        )



    # --------------------------------------------------------
    # Deduplicate edges
    # --------------------------------------------------------

    def unique(
            self,
            items):


        result = []

        seen = set()


        for item in items:


            key = (

                item["from"]

                +

                item["to"]

            )


            if key not in seen:

                seen.add(key)

                result.append(
                    item
                )


        return result
