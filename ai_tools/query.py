"""
query.py

Standalone AI retrieval system.

Reads:

ai/index.json

Searches:

- function names
- signatures
- decompiled C
- assembly
- calls

Returns relevant binary context
for Ollama/Open WebUI.
"""


import os
import json
import re


try:
    from config import OUTPUT_PATH
except ImportError:
    OUTPUT_PATH = None


INDEX_FILE = None



class BinarySearch:

    def __init__(self, path=None):

        if path:
            self.path = path
        else:
            self.path = OUTPUT_PATH

        self.index_file = os.path.join(
            self.path,
            "index.json"
        )

        self.index = {}

        self.load()

    def find(self, name):

        for fn in self.index:

            if fn.get("name") == name:
                return fn

            if fn.get("address") == name:
                return fn

        return None

    @staticmethod
    def safe_text(value):

        if value is None:
            return ""

        if isinstance(value, list):
            return " ".join(
                BinarySearch.safe_text(x)
                for x in value
            )

        if isinstance(value, dict):
            return " ".join(
                BinarySearch.safe_text(v)
                for v in value.values()
            )

        return str(value)

    # --------------------------------------------------------
    # Load index
    # --------------------------------------------------------

    def load(self):

        if not os.path.exists(self.index_file):
            raise Exception(
                "Missing index.json: " + self.index_file
            )

        with open(
            self.index_file,
            "r",
            encoding="utf-8"
        ) as f:
            raw = json.load(f)


        self.index = []


        functions = raw.get(
            "functions",
            {}
        )


        for name, entry in functions.items():

            try:

                function_file = os.path.join(
                    self.path,
                    entry["file"]
                )


                with open(
                    function_file,
                    "r",
                    encoding="utf-8"
                ) as f:

                    fn = json.load(f)


                self.index.append(fn)


            except Exception as e:

                print(
                    "[!] Failed loading {}".format(
                        entry.get(
                            "file",
                            name
                        )
                    )
                )


        print(
            "[+] Loaded {} functions".format(
                len(self.index)
            )
        )


    # --------------------------------------------------------
    # Tokenize
    # --------------------------------------------------------

    def tokenize(
            self,
            text):


        return set(
            re.findall(
                r"[a-zA-Z0-9_]+",
                text.lower()
            )
        )



    # --------------------------------------------------------
    # Score result
    # --------------------------------------------------------
    def score(
            self,
            query,
            item):


        query_tokens = self.tokenize(query)


        name = item.get(
            "name",
            ""
        )

        signature = item.get(
            "signature",
            ""
        )

        assembly = item.get(
            "assembly",
            ""
        )


        comments = " ".join(
            item.get(
                "comments",
                []
            )
            if isinstance(
                item.get("comments", []),
                list
            )
            else [
                str(item.get("comments",""))
            ]
        )


        # Decompiled C
        decompiler = item.get(
            "decompiler",
            {}
        )


        if isinstance(decompiler, dict):

            c_code = decompiler.get(
                "c_code",
                ""
            )

        else:

            c_code = str(decompiler)



        # Calls
        call_text = ""

        for call in item.get("calls", []):

            if isinstance(call, dict):

                call_text += " " + call.get(
                    "name",
                    ""
                )

            else:

                call_text += " " + str(call)


        # External/API references
        external = ""

        for call in item.get("calls", []):

            if isinstance(call, dict):

                if call.get("external"):

                    external += " "
                    external += call.get(
                        "name",
                        ""
                    )


        searchable = [

            (name, 20),

            (signature, 10),

            (comments, 10),

            (call_text, 8),

            (external, 8),

            (c_code, 6),

            (assembly, 1)

        ]


        score = 0


        for text, weight in searchable:

            tokens = self.tokenize(
                text
            )

            matches = (
                query_tokens
                &
                tokens
            )

            score += len(matches) * weight


        return score

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    def search(
            self,
            query,
            limit=5):


        results = []


        if isinstance(self.index, dict):

            items = self.index.values()

        else:

            items = self.index


        for item in items:


            s = self.score(
                query,
                item
            )


            if s > 0:


                results.append({

                    "score":
                        s,

                    "function":
                        item

                })



        results.sort(

            key=lambda x:
                x["score"],

            reverse=True

        )


        return results[:limit]



    # --------------------------------------------------------
    # Build LLM context
    # --------------------------------------------------------

    def context(
            self,
            query,
            limit=5):


        results = self.search(
            query,
            limit
        )


        output = []


        output.append(
            "Relevant binary functions:"
        )


        for result in results:


            fn = result["function"]


            output.append(
                "\n===================="
            )


            output.append(
                "Function: {}".format(
                    fn.get("name", "")
                )
            )


            output.append(
                "Address: {}".format(
                    fn.get("address", "")
                )
            )


            output.append(
                "Signature: {}".format(
                    fn.get("signature", "")
                )
            )


            decompiler = fn.get(
                "decompiler",
                {}
            )


            if isinstance(decompiler, dict):

                c_code = decompiler.get(
                    "c_code",
                    ""
                )

            else:

                c_code = ""


            output.append(
                "\nCalls:"
            )


            for call in fn.get("calls", [])[:15]:

                if isinstance(call, dict):

                    output.append(
                        "- {} {}".format(
                            call.get("name", ""),
                            call.get("address", "")
                        )
                    )


            output.append(
                "\nCalled By:"
            )


            for caller in fn.get("called_by", [])[:15]:

                if isinstance(caller, dict):

                    output.append(
                        "- {} {}".format(
                            caller.get("name", ""),
                            caller.get("address", "")
                        )
                    )


            output.append(
                "\nDecompiled C:\n{}".format(
                    c_code[:5000]
                )
            )


            output.append(
                "\nAssembly:\n{}".format(
                    fn.get(
                        "assembly",
                        ""
                    )[:3000]
                )
            )


        return "\n".join(
            output
        )



# --------------------------------------------------------
# Command line testing
# --------------------------------------------------------

if __name__ == "__main__":


    import sys


    if len(sys.argv) < 2:

        print(
            "Usage:"
        )

        print(
            "python query.py \"search term\""
        )

        exit()



    searcher = BinarySearch()


    print(

        searcher.context(

            sys.argv[1],

            5

        )

    )
