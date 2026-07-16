"""
jsonwriter.py

JSON output helper.

Ghidra ships with an old Python runtime,
so this avoids external dependencies.
"""


import json
import os



class JSONWriter(object):


    @staticmethod
    def save(path, data):


        directory = os.path.dirname(
            path
        )


        if directory and not os.path.exists(directory):

            os.makedirs(directory)



        with open(
            path,
            "w",
            encoding="utf-8",
            errors="replace"
        ) as outfile:


            json.dump(
                data,
                outfile,
                indent=4,
                sort_keys=True,
                ensure_ascii=False
            )



    @staticmethod
    def pretty(data):

        return json.dumps(

            data,

            indent=4,

            sort_keys=True,

            ensure_ascii=False

        )
