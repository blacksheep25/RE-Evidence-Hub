"""
function_summary_exporter.py

Creates AI searchable summaries
from exported function data.

This does not call an AI model.
It creates structured context
for later AI processing.
"""


import os
import json


from util.jsonwriter import JSONWriter



class FunctionSummaryExporter(object):


    VERSION = "1.0.0"



    def __init__(
            self,
            program=None,
            monitor=None,
            output=None,
            config=None):

        self.output = output


        self.function_dir = os.path.join(

            output,

            "functions"

        )



    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    def export(self):


        summaries = []


        if not os.path.exists(
            self.function_dir
        ):


            print(
                "[!] No functions directory"
            )


            return



        files = os.listdir(

            self.function_dir

        )



        for filename in files:


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
                    "r",
                    encoding="utf-8",
                    errors="replace"
                ) as f:

                    function = json.load(f)



                summary = (
                    self.create_summary(
                        function
                    )
                )


                summaries.append(
                    summary
                )



            except Exception as e:


                print(

                    "[!] Failed {} : {}".format(

                        filename,

                        e

                    )

                )



        output = os.path.join(

            self.output,

            "function_summaries.json"

        )



        JSONWriter.save(

            output,

            summaries

        )


        print(

            "[+] Function summaries exported: {}".format(

                len(summaries)

            )

        )



    # --------------------------------------------------------
    # Create summary
    # --------------------------------------------------------

    def create_summary(
            self,
            function):


        evidence = []


        calls = function.get(

            "calls",

            []

        )


        for call in calls:


            if call.get("name"):


                evidence.append(

                    call["name"]

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



        summary = {


            "address":

                function.get(
                    "address"
                ),


            "name":

                function.get(
                    "name"
                ),



            "signature":

                function.get(
                    "signature"
                ),



            "size":

                function.get(
                    "size"
                ),



            "summary":

                self.generate_description(

                    function,

                    evidence

                ),



            "evidence":

                evidence[:50],



            "has_decompiler":

                len(c_code) > 0,



            "hash":

                function.get(
                    "hash"
                )

        }



        return summary



    # --------------------------------------------------------
    # Basic classification
    # --------------------------------------------------------

    def generate_description(
            self,
            function,
            evidence):


        text = "Unknown functionality"



        joined = " ".join(

            evidence

        ).lower()



        if any(x in joined for x in [

            "socket",

            "connect",

            "recv",

            "send"

        ]):


            text = (

                "Likely network related function"

            )



        elif any(x in joined for x in [

            "createfile",

            "readfile",

            "writefile"

        ]):


            text = (

                "Likely file handling function"

            )



        elif any(x in joined for x in [

            "crypt",

            "aes",

            "sha",

            "hash"

        ]):


            text = (

                "Likely cryptographic function"

            )



        elif any(x in joined for x in [

            "malloc",

            "free",

            "heap"

        ]):


            text = (

                "Likely memory management function"

            )



        return text
