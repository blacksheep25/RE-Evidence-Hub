"""
investigation_loop.py

Autonomous reverse engineering investigation engine.

Responsibilities:

- Read triage results
- Create hypotheses
- Track investigation progress
- Store findings
- Generate next actions

This is the planning layer between tools and the AI model.
"""


import os
import json
import datetime



from investigation_memory import InvestigationMemory
from analysis_tools import AnalysisTools



class InvestigationLoop:


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.tools = AnalysisTools(

            export_path

        )


        self.memory = InvestigationMemory(

            export_path

        )


        self.triage = self.load_triage()



    # -------------------------------------------------
    # Load triage
    # -------------------------------------------------

    def load_triage(self):


        path = os.path.join(

            self.export_path,

            "triage_report.json"

        )


        if os.path.exists(path):


            with open(

                path,

                "r",

                encoding="utf-8"

            ) as f:


                return json.load(f)



        return {}



    # -------------------------------------------------
    # Create initial hypotheses
    # -------------------------------------------------

    def create_hypotheses(self):


        subsystems = self.triage.get(

            "subsystems",

            []

        )


        for subsystem in subsystems:


            name = subsystem.get(

                "subsystem"

            )


            if name == "authentication":


                self.memory.add_hypothesis(

                    "Binary contains an authentication subsystem",

                    "medium"

                )



            elif name == "networking":


                self.memory.add_hypothesis(

                    "Binary contains network communication handlers",

                    "medium"

                )



            elif name == "cryptography":


                self.memory.add_hypothesis(

                    "Binary contains cryptographic functionality",

                    "medium"

                )



    # -------------------------------------------------
    # Find interesting functions
    # -------------------------------------------------

    def identify_targets(self):


        targets = []


        keywords = [

            "login",

            "auth",

            "crypt",

            "encrypt",

            "connect",

            "send",

            "recv",

            "password"

        ]



        for keyword in keywords:


            results = self.tools.search(

                keyword

            )


            for item in results:


                targets.append(item)



        unique = {}



        for item in targets:


            unique[

                item["address"]

            ] = item



        return list(unique.values())



    # -------------------------------------------------
    # Analyze targets
    # -------------------------------------------------

    def analyze_targets(self):


        targets = self.identify_targets()



        for target in targets:


            function = self.tools.get_function(

                target["address"]

            )



            if not function:

                continue



            signals = []



            text = json.dumps(

                function

            ).lower()



            if "recv" in text:

                signals.append(

                    "network receive"

                )


            if "strcmp" in text:

                signals.append(

                    "string comparison"

                )


            if "encrypt" in text:

                signals.append(

                    "encryption reference"

                )



            if signals:


                self.memory.add_finding(

                    target["name"],

                    "Potential important function",

                    signals,

                    "medium"

                )



    # -------------------------------------------------
    # Produce next actions
    # -------------------------------------------------

    def generate_next_actions(self):


        actions = [

            "Inspect highest confidence functions",

            "Trace callers of authentication routines",

            "Review network handlers",

            "Identify encryption boundaries",

            "Map external APIs"

        ]



        self.memory.add_note(

            "Recommended actions:\n" +

            "\n".join(actions)

        )



    # -------------------------------------------------
    # Run
    # -------------------------------------------------

    def run(self):


        print(

            "[+] Creating hypotheses"

        )


        self.create_hypotheses()



        print(

            "[+] Analyzing targets"

        )


        self.analyze_targets()



        print(

            "[+] Generating next actions"

        )


        self.generate_next_actions()



        print(

            "[+] Investigation loop complete"

        )





if __name__ == "__main__":


    import sys


    if len(sys.argv) != 2:


        print(

            "Usage: python investigation_loop.py <export folder>"

        )


        sys.exit(1)



    InvestigationLoop(

        sys.argv[1]

    ).run()
