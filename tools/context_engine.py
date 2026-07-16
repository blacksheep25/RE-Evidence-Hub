"""
context_engine.py

Builds optimized AI context.

Responsibilities:

- Select relevant evidence
- Rank functions
- Limit context size
- Include investigation memory
- Create AI-ready context packages
"""


import os
import json



from analysis_tools import AnalysisTools
from investigation_memory import InvestigationMemory



class ContextEngine:


    def __init__(
            self,
            export_path,
            max_functions=20):


        self.export_path = export_path

        self.max_functions = max_functions


        self.tools = AnalysisTools(

            export_path

        )


        self.memory = InvestigationMemory(

            export_path

        )



    # -------------------------------------------------
    # Score function relevance
    # -------------------------------------------------

    def score_function(
            self,
            function,
            keywords):


        score = 0


        text = json.dumps(

            function

        ).lower()



        for keyword in keywords:


            if keyword.lower() in text:

                score += 1



        return score



    # -------------------------------------------------
    # Find relevant functions
    # -------------------------------------------------

    def find_relevant_functions(
            self,
            query):


        keywords = query.lower().split()



        ranked = []



        for address,function in self.tools.functions.items():


            score = self.score_function(

                function,

                keywords

            )


            if score > 0:


                ranked.append({

                    "score":

                        score,


                    "address":

                        address,


                    "function":

                        function

                })



        ranked.sort(

            key=lambda x:

                x["score"],

            reverse=True

        )


        return ranked[:self.max_functions]



    # -------------------------------------------------
    # Expand relationships
    # -------------------------------------------------

    def expand_function(
            self,
            item):


        address = item["address"]



        result = {


            "function":

                item["function"],


            "callers":

                self.tools.get_callers(

                    address

                ),


            "callees":

                self.tools.get_callees(

                    address

                )

        }


        return result



    # -------------------------------------------------
    # Build context
    # -------------------------------------------------

    def build_context(
            self,
            query):


        functions = self.find_relevant_functions(

            query

        )


        expanded = []


        for function in functions:


            expanded.append(

                self.expand_function(

                    function

                )

            )



        context = {


            "task":

                query,


            "investigation_memory":

                json.loads(

                    self.memory.context()

                ),


            "relevant_functions":

                expanded

        }



        return context



    # -------------------------------------------------
    # Save context package
    # -------------------------------------------------

    def save_context(
            self,
            query):


        context = self.build_context(

            query

        )


        path = os.path.join(

            self.export_path,

            "ai_context.json"

        )



        with open(

            path,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                context,

                f,

                indent=2

            )



        return path





if __name__ == "__main__":


    import sys


    if len(sys.argv) < 3:


        print(

            "Usage: python context_engine.py <export> <query>"

        )

        sys.exit(1)



    engine = ContextEngine(

        sys.argv[1]

    )


    print(

        engine.save_context(

            " ".join(sys.argv[2:])

        )

    )
