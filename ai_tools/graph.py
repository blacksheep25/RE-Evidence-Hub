import json
import os


class BinaryGraph:

    def __init__(self, export_path):

        self.path = export_path

        self.callgraph = {}

        self.load()


    def load(self):

        filename = os.path.join(
            self.path,
            "callgraph.json"
        )

        if os.path.exists(filename):

            with open(filename,"r") as f:

                self.callgraph = json.load(f)


    def neighbours(self,name):

        if name not in self.callgraph:

            return []

        return self.callgraph[name]
