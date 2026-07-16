import os
import json


class BinaryTypes:


    def __init__(self, export_path):

        self.path = os.path.join(
            export_path,
            "types"
        )

        self.types = []

        self.load()



    def load(self):

        if not os.path.exists(self.path):

            print(
                "[!] No types directory"
            )

            return


        for root, dirs, files in os.walk(self.path):

            for file in files:

                if not file.endswith(".json"):
                    continue


                filename = os.path.join(
                    root,
                    file
                )

                try:

                    with open(
                        filename,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        data=json.load(f)


                    self.types.append(
                        data
                    )

                except Exception:

                    pass


        print(
            "[+] Loaded types:",
            len(self.types)
        )



    def search(
        self,
        query,
        limit=10
    ):

        query=query.lower()

        results=[]


        for t in self.types:

            blob=json.dumps(
                t
            ).lower()


            if query in blob:

                results.append(
                    t
                )


        return results[:limit]
