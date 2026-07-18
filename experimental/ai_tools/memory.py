import os
import json


class BinaryMemory:


    def __init__(self, export_path):

        self.export_path = export_path

        self.memory_file = os.path.join(
            export_path,
            "memory_map.json"
        )

        self.memory = {}

        self.load()



    def load(self):

        if not os.path.exists(self.memory_file):

            print(
                "[!] No memory_map.json found"
            )

            return


        with open(
            self.memory_file,
            "r",
            encoding="utf-8"
        ) as f:

            raw = json.load(f)


        # Support list format
        if isinstance(raw, list):

            self.memory = {}

            for item in raw:

                if isinstance(item, dict):

                    address = (
                        item.get("address")
                        or
                        item.get("name")
                        or
                        ""
                    )

                    if address:
                        self.memory[address] = item


        # Support dictionary format
        elif isinstance(raw, dict):

            self.memory = raw


        else:

            self.memory = {}


        print(
            "[+] Loaded memory map:",
            len(self.memory),
            "entries"
        )


    def search(self, query):

        results = []

        query = query.lower()


        for key,value in self.memory.items():

            blob = json.dumps(
                value
            ).lower()


            if query in blob or key.lower() in query:

                results.append(
                    {
                        "address": key,
                        "data": value
                    }
                )


        return results[:10]
