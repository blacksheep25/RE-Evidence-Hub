"""
llm_interface.py

Connects the reverse engineering
knowledge base to an LLM.

Features:

- semantic retrieval
- evidence injection
- prompt construction
- chat interface

Requires:

pip install requests sentence-transformers numpy
"""


import os
import json
import sys


import requests
import numpy as np


from sentence_transformers import SentenceTransformer



class LLMInterface(object):


    def __init__(
            self,
            export_path,
            api_url,
            model):


        self.export_path = export_path

        self.api_url = api_url

        self.model_name = model


        self.embedder = SentenceTransformer(

            "all-MiniLM-L6-v2"

        )


        self.load()



    # --------------------------------------------------------
    # Load knowledge base
    # --------------------------------------------------------

    def load(self):


        vector_dir = os.path.join(

            self.export_path,

            "vectors"

        )


        self.vectors = np.load(

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


            self.chunks = json.load(f)



        evidence = os.path.join(

            self.export_path,

            "evidence_database.json"

        )


        if os.path.exists(evidence):


            with open(

                evidence,

                "r",

                encoding="utf-8"

            ) as f:


                self.evidence = json.load(f)


        else:


            self.evidence = {}



        report = os.path.join(

            self.export_path,

            "reverse_engineering_report.md"

        )


        if os.path.exists(report):


            with open(

                report,

                "r",

                encoding="utf-8"

            ) as f:


                self.report = f.read()


        else:


            self.report = ""



    # --------------------------------------------------------
    # Retrieve context
    # --------------------------------------------------------

    def retrieve(
            self,
            question,
            limit=6):


        query_vector = self.embedder.encode(

            question,

            convert_to_numpy=True

        )



        scores = np.dot(

            self.vectors,

            query_vector

        )



        indexes = np.argsort(

            scores

        )[::-1]



        results = []



        for index in indexes[:limit]:


            results.append(

                self.chunks[index]

            )



        return results



    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    def build_prompt(
            self,
            question):


        context = ""


        results = self.retrieve(

            question

        )


        for item in results:


            context += """

============================

FUNCTION

Name:
{}


Address:
{}


DATA:

{}

""".format(

                item["metadata"]["name"],

                item["metadata"]["address"],

                item["content"]

            )



        prompt = """

You are an expert reverse engineer.

You are analyzing a binary using
a Ghidra static analysis export.


Rules:

- Only make claims supported by evidence.
- Include function addresses.
- Explain reasoning.
- Identify uncertainty.
- Reference calls, strings, and imports.


Binary report:

{}


Question:

{}


Relevant evidence:

{}

Provide your analysis.

""".format(

            self.report[:5000],

            question,

            context

        )


        return prompt



    # --------------------------------------------------------
    # Send to LLM
    # --------------------------------------------------------

    def ask(
            self,
            question):


        prompt = self.build_prompt(

            question

        )


        payload = {


            "model":

                self.model_name,


            "messages":

            [

                {

                    "role":

                        "user",


                    "content":

                        prompt

                }

            ]

        }



        response = requests.post(

            self.api_url,

            json=payload,

            timeout=300

        )


        response.raise_for_status()



        data = response.json()



        return data



    # --------------------------------------------------------
    # Chat loop
    # --------------------------------------------------------

    def chat(self):


        print(

            "AI Reverse Engineering Assistant"

        )


        while True:


            question = input(

                "\n> "

            )



            if question.lower() in [

                "exit",

                "quit"

            ]:


                break



            answer = self.ask(

                question

            )


            print(

                json.dumps(

                    answer,

                    indent=2

                )

            )





if __name__ == "__main__":


    if len(sys.argv) < 4:


        print(

            """

Usage:

python llm_interface.py

<export folder>

<api url>

<model>


Example:

python llm_interface.py export http://localhost:11434/api/chat llama3

"""

        )


        sys.exit(1)



    interface = LLMInterface(

        sys.argv[1],

        sys.argv[2],

        sys.argv[3]

    )


    interface.chat()
