"""
embedding_exporter.py

Creates AI/RAG chunks from exported
Ghidra function JSON files.

Output:

ai_chunks.json

Each chunk contains:
- searchable text
- metadata
- function identity
"""


import os
import json


from util.jsonwriter import JSONWriter



class EmbeddingExporter(object):


    VERSION = "1.0.0"



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


        self.function_dir = os.path.join(

            output,

            "functions"

        )



    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    def export(self):


        chunks = []


        if not os.path.exists(
            self.function_dir
        ):


            print(
                "[!] Function directory missing"
            )


            return



        for filename in os.listdir(
            self.function_dir
        ):


            if not filename.endswith(
                ".json"
            ):

                continue



            path = os.path.join(

                self.function_dir,

                filename

            )



            try:


                with open(
                    path,
                    "r"
                ) as f:


                    function = json.load(f)



                chunk = (
                    self.create_chunk(
                        function
                    )
                )


                chunks.append(
                    chunk
                )



            except Exception as e:


                print(

                    "[!] Failed {} {}".format(

                        filename,

                        e

                    )

                )



        output = os.path.join(

            self.output,

            "ai_chunks.json"

        )



        JSONWriter.save(

            output,

            chunks

        )



        print(

            "[+] AI chunks exported: {}".format(

                len(chunks)

            )

        )



    # --------------------------------------------------------
    # Create chunk
    # --------------------------------------------------------

    def create_chunk(
            self,
            function):


        address = function.get(

            "address",

            ""

        )


        name = function.get(

            "name",

            ""

        )


        signature = function.get(

            "signature",

            ""

        )


        assembly = function.get(

            "assembly",

            ""

        )


        decompiler = function.get(

            "decompiler",

            {}

        )


        c_code = ""



        if isinstance(
            decompiler,
            dict
        ):


            c_code = decompiler.get(

                "c_code",

                ""

            )



        calls = []


        for call in function.get(

            "calls",

            []

        ):


            calls.append(

                call.get(

                    "name",

                    ""

                )

            )



        content = """

FUNCTION

Name:
{}



Address:
{}



Signature:
{}



Calls:

{}



Decompiler:

{}



Assembly:

{}

""".format(

            name,

            address,

            signature,

            "\n".join(
                calls
            ),

            c_code,

            assembly

        )



        return {


            "id":

                "function_" + address,



            "type":

                "function",



            "content":

                content,



            "metadata":

            {


                "address":

                    address,


                "name":

                    name,


                "signature":

                    signature

            }

        }
