"""
vector_query.py

Semantic search over
Ghidra AI export.

Usage:

python vector_query.py <export> "question"
"""


import os
import json
import sys


import numpy as np


from sentence_transformers import SentenceTransformer



class VectorQuery(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.model = SentenceTransformer(

            "all-MiniLM-L6-v2"

        )


        self.load()



    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    def load(self):


        vector_dir = os.path.join(

            self.export_path,

            "vectors"

        )


        self.embeddings = np.load(

            os.path.join(

                vector_dir,

                "embeddings.npy"

            )

        )


        with open(

            os.path.join(

                vector_dir,

                "metadata.json"

            ),

            "r",

            encoding="utf-8"

        ) as f:


            self.metadata = json.load(f)



    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    def search(
            self,
            query,
            limit=5):


        vector = self.model.encode(

            query,

            convert_to_numpy=True

        )



        scores = np.dot(

            self.embeddings,

            vector

        )



        indexes = np.argsort(

            scores

        )[::-1]



        results = []



        for index in indexes[:limit]:


            results.append({

                "score":

                    float(
                        scores[index]
                    ),

                "chunk":

                    self.metadata[index]

            })



        return results




if __name__ == "__main__":


    if len(sys.argv) < 3:


        print(

            "Usage: vector_query.py <export> <query>"

        )


        sys.exit(1)



    engine = VectorQuery(

        sys.argv[1]

    )


    query = " ".join(

        sys.argv[2:]

    )



    results = engine.search(

        query

    )


    for result in results:


        chunk = result["chunk"]


        print(

            "\n===================="

        )


        print(

            "Score:",

            result["score"]

        )


        print(

            "Function:",

            chunk["metadata"]["name"]

        )


        print(

            "Address:",

            chunk["metadata"]["address"]

        )


        print(

            chunk["content"][:1000]

        )
