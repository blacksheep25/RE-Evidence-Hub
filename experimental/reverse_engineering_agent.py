"""
reverse_engineering_agent.py

AI reverse engineering assistant backend.

Responsibilities:

- Load vector index
- Search binary knowledge base
- Retrieve function context
- Build prompts for an LLM

This script does not call an LLM.
It prepares the intelligence layer.
"""


import os
import json
import sys


import numpy as np


from sentence_transformers import SentenceTransformer



class ReverseEngineeringAgent(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.model = SentenceTransformer(

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


            self.functions = json.load(f)



        context_path = os.path.join(

            self.export_path,

            "ai_context.json"

        )


        with open(

            context_path,

            "r",

            encoding="utf-8"

        ) as f:


            self.context = json.load(f)



    # --------------------------------------------------------
    # Semantic search
    # --------------------------------------------------------

    def search_functions(
            self,
            question,
            limit=5):


        vector = self.model.encode(

            question,

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

                "function":

                    self.functions[index]

            })



        return results



    # --------------------------------------------------------
    # Build LLM prompt
    # --------------------------------------------------------

    def build_prompt(
            self,
            question):


        matches = self.search_functions(

            question,

            8

        )



        prompt = """

You are an expert reverse engineer.

You are analyzing a binary using a Ghidra static analysis export.


Binary:

{}



Question:

{}



Relevant functions:

""".format(

            self.context["binary"]["name"],

            question

        )



        for match in matches:


            function = match["function"]


            prompt += """

--------------------------------

Function:

{}

Address:

{}

Confidence:

{}


Evidence:

{}

Context:

{}

""".format(

                function["metadata"]["name"],

                function["metadata"]["address"],

                match["score"],

                function["content"][:1500],

                ""

            )



        prompt += """

--------------------------------


Instructions:

- Explain behaviour.
- Cite addresses.
- Identify evidence.
- Mention uncertainty.
- Follow call relationships.
- Do not invent behaviour.


Answer:

"""


        return prompt



    # --------------------------------------------------------
    # Interactive mode
    # --------------------------------------------------------

    def chat(self):


        print(

            "Reverse Engineering Agent"

        )


        print(

            "Type exit to quit"

        )



        while True:


            question = input(

                "\n> "

            )



            if question.lower() == "exit":

                break



            print(

                self.build_prompt(

                    question

                )

            )





if __name__ == "__main__":


    if len(sys.argv) != 2:


        print(

            "Usage: reverse_engineering_agent.py <export folder>"

        )


        sys.exit(1)



    agent = ReverseEngineeringAgent(

        sys.argv[1]

    )


    agent.chat()
