import os
import json


class StringSearch:

    def __init__(self, export_path):

        self.file = os.path.join(
            export_path,
            "strings.json"
        )

        self.strings = []

        self.load()


    def load(self):

        if not os.path.exists(self.file):
            print("[!] No strings.json")
            return


        with open(
            self.file,
            "r",
            encoding="utf-8"
        ) as f:

            data=json.load(f)


        if isinstance(data, list):
            self.strings=data

        elif isinstance(data, dict):
            self.strings=list(data.values())


        print(
            f"[+] Loaded strings: {len(self.strings)}"
        )


    def search(self, query):

        query=query.lower()

        results=[]

        for s in self.strings:

            blob=json.dumps(s).lower()

            if query in blob:

                results.append(s)


        return results[:20]
