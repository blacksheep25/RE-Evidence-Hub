"""
vector_indexer.py

Creates a local semantic index
from Ghidra AI chunks.

Requires:

pip install sentence-transformers numpy
"""


import os
import json
import sys


import numpy as np


from sentence_transformers import SentenceTransformer



class VectorIndexer(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.model = SentenceTransformer(

            "all-MiniLM-L6-v2"

        )


        self.chunks = []



    # --------------------------------------------------------
    # Load chunks
    # --------------------------------------------------------

    def load(self):


        path = os.path.join(

            self.export_path,

            "ai_chunks.json"

        )


        if not os.path.exists(path):

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
    # Build index
    # --------------------------------------------------------

    def build(self):


        self.load()



        texts = []


        for chunk in self.chunks:


            texts.append(

                chunk["content"]

            )



        print(

            "[+] Creating embeddings..."

        )


        embeddings = self.model.encode(

            texts,

            show_progress_bar=True,

            convert_to_numpy=True

        )



        index_dir = os.path.join(

            self.export_path,

            "vectors"

        )


        if not os.path.exists(index_dir):

            os.makedirs(index_dir)



        np.save(

            os.path.join(

                index_dir,

                "embeddings.npy"

            ),

            embeddings

        )



        with open(

            os.path.join(

                index_dir,

                "metadata.json"

            ),

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                self.chunks,

                f,

                indent=2

            )



        print(

            "[+] Vector index created"

        )





if __name__ == "__main__":


    if len(sys.argv) != 2:


        print(

            "Usage: vector_indexer.py <export folder>"

        )


        sys.exit(1)



    indexer = VectorIndexer(

        sys.argv[1]

    )


    indexer.build()
