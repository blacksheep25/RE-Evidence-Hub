"""
investigation_memory.py

Persistent memory for reverse engineering sessions.

Stores:

- Findings
- Hypotheses
- Confirmed behavior
- Analyst notes
- Questions
- Confidence scores

File:

investigation_memory.json
"""


import os
import json
import datetime



class InvestigationMemory:


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.file = os.path.join(

            export_path,

            "investigation_memory.json"

        )


        self.data = {


            "created":

                str(

                    datetime.datetime.now()

                ),


            "findings":

                [],


            "hypotheses":

                [],


            "notes":

                [],


            "questions":

                []

        }


        self.load()



    # -------------------------------------------------
    # Load memory
    # -------------------------------------------------

    def load(self):


        if os.path.exists(self.file):


            with open(

                self.file,

                "r",

                encoding="utf-8"

            ) as f:


                self.data = json.load(f)



    # -------------------------------------------------
    # Save
    # -------------------------------------------------

    def save(self):


        self.data["updated"] = (

            str(

                datetime.datetime.now()

            )

        )


        with open(

            self.file,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                self.data,

                f,

                indent=2

            )



    # -------------------------------------------------
    # Add finding
    # -------------------------------------------------

    def add_finding(
            self,
            title,
            description,
            evidence,
            confidence="medium"):


        self.data["findings"].append({

            "title":

                title,


            "description":

                description,


            "evidence":

                evidence,


            "confidence":

                confidence,


            "created":

                str(

                    datetime.datetime.now()

                )

        })


        self.save()



    # -------------------------------------------------
    # Add hypothesis
    # -------------------------------------------------

    def add_hypothesis(
            self,
            statement,
            confidence="low"):


        self.data["hypotheses"].append({

            "statement":

                statement,


            "confidence":

                confidence,


            "status":

                "open"

        })


        self.save()



    # -------------------------------------------------
    # Confirm hypothesis
    # -------------------------------------------------

    def confirm_hypothesis(
            self,
            index):


        if index < len(

            self.data["hypotheses"]

        ):


            self.data["hypotheses"][index]["status"] = (

                "confirmed"

            )


            self.save()



    # -------------------------------------------------
    # Add note
    # -------------------------------------------------

    def add_note(
            self,
            note):


        self.data["notes"].append({

            "text":

                note,


            "time":

                str(

                    datetime.datetime.now()

                )

        })


        self.save()



    # -------------------------------------------------
    # Add question
    # -------------------------------------------------

    def add_question(
            self,
            question):


        self.data["questions"].append(

            question

        )


        self.save()



    # -------------------------------------------------
    # Context export
    # -------------------------------------------------

    def context(self):


        return json.dumps(

            self.data,

            indent=2

        )





if __name__ == "__main__":


    import sys


    memory = InvestigationMemory(

        sys.argv[1]

    )


    print(

        memory.context()

    )
