"""
query_engine.py

Local AI search interface.

Searches exported Ghidra AI chunks.

Usage:

python query_engine.py export_folder "search term"

Example:

python query_engine.py ^
"C:\\exports\\game.exe" ^
"network login"


Returns:

- matching functions
- addresses
- evidence
- code context
"""


import os
import json
import sys



class QueryEngine(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.chunks = []


        self.load()



    # --------------------------------------------------------
    # Load chunks
    # --------------------------------------------------------

    def load(self):


        path = os.path.join(

            self.export_path,

            "ai_chunks.json"

        )


        if not os.path.exists(
            path
        ):


            raise RuntimeError(

                "ai_chunks.json missing"

            )



        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:


            self.chunks = json.load(f)



        print(

            "[+] Loaded {} chunks".format(

                len(self.chunks)

            )

        )



    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    def search(
            self,
            query,
            limit=10):


        query_words = [

            x.lower()

            for x in query.split()

        ]



        results = []



        for chunk in self.chunks:


            text = chunk.get(

                "content",

                ""

            ).lower()



            score = 0



            for word in query_words:


                if word in text:

                    score += 1



            if score > 0:


                results.append({

                    "score":

                        score,

                    "chunk":

                        chunk

                })



        results.sort(

            key=lambda x:

                x["score"],

            reverse=True

        )


        return results[:limit]



    # --------------------------------------------------------
    # Format for AI
    # --------------------------------------------------------

    def ai_context(
            self,
            query):


        results = self.search(
            query
        )


        output = []


        for result in results:


            chunk = result["chunk"]


            output.append(

                """

----------------------------

FUNCTION

Name:
{}


Address:
{}


CONTENT:

{}

""".format(

                chunk["metadata"]["name"],

                chunk["metadata"]["address"],

                chunk["content"]

                )

            )


        return "\n".join(output)



# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------


if __name__ == "__main__":


    if len(sys.argv) < 3:


        print(

            "Usage: query_engine.py <export> <query>"

        )


        sys.exit(1)



    engine = QueryEngine(

        sys.argv[1]

    )


    query = " ".join(

        sys.argv[2:]

    )



    print(

        engine.ai_context(

            query

        )

    )
