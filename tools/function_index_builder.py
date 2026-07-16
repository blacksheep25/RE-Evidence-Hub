"""
function_index_builder.py

Creates a lightweight searchable function database.

Reads:

functions/*.json

Creates:

function_index.json

The index contains:

- Function name
- Address
- Size
- Strings
- Imports
- Call relationships
- Risk score

The AI uses this before loading full function data.
"""


import os
import json



class FunctionIndexBuilder:


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.functions_path = os.path.join(

            export_path,

            "functions"

        )


        self.output = os.path.join(

            export_path,

            "function_index.json"

        )



    # -------------------------------------------------
    # Score importance
    # -------------------------------------------------

    def calculate_score(
            self,
            function):


        score = 0


        text = json.dumps(

            function

        ).lower()



        indicators = {


            "password":
                20,


            "login":
                20,


            "auth":
                15,


            "token":
                15,


            "encrypt":
                20,


            "decrypt":
                20,


            "crypto":
                15,


            "socket":
                15,


            "connect":
                10,


            "recv":
                10,


            "send":
                10,


            "http":
                10,


            "file":
                5

        }



        for keyword,value in indicators.items():


            if keyword in text:

                score += value



        return min(

            score,

            100

        )



    # -------------------------------------------------
    # Extract index entry
    # -------------------------------------------------

    def create_entry(
            self,
            data):


        return {


            "address":

                data.get(

                    "address"

                ),



            "name":

                data.get(

                    "name"

                ),



            "size":

                data.get(

                    "size",

                    0

                ),



            "signature":

                data.get(

                    "signature",

                    ""

                ),



            "instruction_count":

                data.get(

                    "instruction_count",

                    0

                ),



            "calls":

                data.get(

                    "calls",

                    []

                ),



            "called_by":

                data.get(

                    "called_by",

                    []

                ),



            "risk_score":

                self.calculate_score(

                    data

                )

        }



    # -------------------------------------------------
    # Build index
    # -------------------------------------------------

    def build(self):


        index = {}


        if not os.path.exists(

            self.functions_path

        ):


            print(

                "[!] No functions directory"

            )

            return



        count = 0



        for filename in os.listdir(

            self.functions_path

        ):


            if not filename.endswith(

                ".json"

            ):

                continue



            path = os.path.join(

                self.functions_path,

                filename

            )



            try:


                with open(

                    path,

                    "r",

                    encoding="utf-8",

                    errors="replace"

                ) as f:


                    data = json.load(f)



                entry = self.create_entry(

                    data

                )



                address = entry["address"]



                if address:


                    index[address] = entry



                count += 1



            except Exception as e:


                print(

                    "Failed:",

                    filename,

                    e

                )



        with open(

            self.output,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                index,

                f,

                indent=2

            )



        print(

            "[+] Indexed {} functions"

            .format(

                count

            )

        )


        print(

            "[+] Saved:",

            self.output

        )





if __name__ == "__main__":


    import sys


    if len(sys.argv) != 2:


        print(

            "Usage: python function_index_builder.py <export folder>"

        )


        exit(1)



    builder = FunctionIndexBuilder(

        sys.argv[1]

    )


    builder.build()
