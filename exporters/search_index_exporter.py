"""
search_index_exporter.py

Creates an AI-friendly search index.

Output:

index.json

Contains references to:

- Functions
- Strings
- Imports
- Types
- Globals
"""


import os
import json


from util.jsonwriter import JSONWriter



class SearchIndexExporter(object):

    VERSION = "2.0"


    def __init__(
            self,
            program=None,
            monitor=None,
            output=None,
            config=None):

        self.output = output

        self.program = program
        self.monitor = monitor
        self.output = output
        self.config = config


        self.index = {


            "version":
                self.VERSION,


            "functions":
                {},


            "function_names":
                {},


            "strings":
                {},


            "imports":
                {},


            "types":
                {},


            "globals":
                {}

        }



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        print(
            "[+] Building search index"
        )


        self.index_functions()

        self.index_strings()

        self.index_imports()

        self.index_types()

        self.index_globals()



        path = os.path.join(

            self.output,

            "index.json"

        )


        JSONWriter.save(

            path,

            self.index

        )


        print(
            "[+] Search index created"
        )



    # --------------------------------------------------------
    # Functions
    # --------------------------------------------------------

    def index_functions(self):


        directory = os.path.join(

            self.output,

            "functions"

        )


        if not os.path.exists(directory):

            return



        for filename in sorted(os.listdir(directory)):


            if not filename.endswith(
                ".json"
            ):

                continue



            path = os.path.join(

                directory,

                filename

            )

            with open(
                path,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as f:

                function = json.load(f)

            # Addresses are stable and match functions/<address>.json. Names
            # are mutable in Ghidra and can be duplicated in C++ binaries.
            address = function["address"]


            self.index["functions"][

                address

            ] = {


                "address":

                    address,


                "name":

                    function.get("name", ""),


                "file":

                    "functions/" + filename


            }


            name = function.get("name", "")


            if name:


                if name not in self.index["function_names"]:


                    self.index["function_names"][name] = []


                self.index["function_names"][name].append(address)



    # --------------------------------------------------------
    # Strings
    # --------------------------------------------------------

    def index_strings(self):


        path = os.path.join(

            self.output,

            "strings.json"

        )


        if not os.path.exists(path):

            return



        with open(path, "r") as f:


            strings = json.load(f)



        for item in strings:


            value = item.get(

                "value",

                ""

            )


            if value:


                self.index["strings"][

                    value

                ] = {


                    "address":

                        item.get(
                            "address"
                        ),


                    "functions":

                        item.get(
                            "functions",
                            []
                        )

                }



    # --------------------------------------------------------
    # Imports
    # --------------------------------------------------------

    def index_imports(self):


        path = os.path.join(

            self.output,

            "imports.json"

        )


        if not os.path.exists(path):

            return



        with open(path, "r") as f:


            imports = json.load(f)



        for item in imports:


            self.index["imports"][

                item.get(
                    "name",
                    ""
                )

            ] = item



    # --------------------------------------------------------
    # Types
    # --------------------------------------------------------

    def index_types(self):


        directory = os.path.join(

            self.output,

            "types"

        )


        if not os.path.exists(directory):

            return



        for filename in os.listdir(directory):


            if not filename.endswith(
                ".json"
            ):

                continue



            path = os.path.join(

                directory,

                filename

            )


            with open(path, "r") as f:


                data = json.load(f)



            for item in data:


                name = item.get(

                    "name",

                    ""

                )


                if name:


                    self.index["types"][

                        name

                    ] = {


                        "file":

                            "types/" + filename

                    }



    # --------------------------------------------------------
    # Globals
    # --------------------------------------------------------

    def index_globals(self):


        path = os.path.join(

            self.output,

            "globals.json"

        )


        if not os.path.exists(path):

            return



        with open(path, "r") as f:


            globals = json.load(f)



        for item in globals:


            name = item.get(

                "name",

                ""

            )


            if name:


                self.index["globals"][

                    name

                ] = item
