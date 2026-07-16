import json
import os


class CallGraph:


    def __init__(self, export_path):

        self.export_path = export_path

        self.graph_file = os.path.join(
            export_path,
            "callgraph.json"
        )

        self.graph = {}

        self.load()



    def load(self):

        if not os.path.exists(
            self.graph_file
        ):

            print(
                "[!] No callgraph.json found"
            )

            return


        with open(
            self.graph_file,
            "r",
            encoding="utf-8"
        ) as f:

            self.graph = json.load(f)


        print(
            "[+] Loaded call graph"
        )



    def get_children(
        self,
        address
    ):

        results = []


        node = self.graph.get(
            address,
            {}
        )


        for item in node.get(
            "calls",
            []
        ):

            if isinstance(
                item,
                dict
            ):

                results.append(
                    item.get(
                        "address",
                        ""
                    )
                )


        return results



    def get_parents(
        self,
        address
    ):

        results = []


        node = self.graph.get(
            address,
            {}
        )


        for item in node.get(
            "called_by",
            []
        ):

            if isinstance(
                item,
                dict
            ):

                results.append(
                    item.get(
                        "address",
                        ""
                    )
                )


        return results



    def expand(
        self,
        address,
        depth=1
    ):

        found = set()


        def walk(addr, level):

            if level > depth:
                return


            if addr in found:
                return


            found.add(addr)


            for child in self.get_children(addr):

                walk(
                    child,
                    level + 1
                )


            for parent in self.get_parents(addr):

                walk(
                    parent,
                    level + 1
                )


        walk(
            address,
            0
        )


        return list(found)
