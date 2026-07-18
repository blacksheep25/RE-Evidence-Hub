"""
agent_controller.py

Autonomous reverse engineering controller.

Takes a question/task and decides
which analysis modules to run.

Example:

python agent_controller.py export \
"find authentication"

"""


import os
import sys
import json
import datetime


# Resolve tools.* / experimental.* whether run as a script or imported.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tools.evidence_collector import EvidenceCollector
from tools.report_generator import ReportGenerator



class AgentController(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.memory = []


        self.load_memory()



    # --------------------------------------------------
    # Memory
    # --------------------------------------------------

    def load_memory(self):


        path = os.path.join(

            self.export_path,

            "agent_memory.json"

        )


        if os.path.exists(path):


            with open(

                path,

                "r",

                encoding="utf-8"

            ) as f:


                self.memory = json.load(f)



    def save_memory(self):


        path = os.path.join(

            self.export_path,

            "agent_memory.json"

        )


        with open(

            path,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                self.memory,

                f,

                indent=2

            )



    # --------------------------------------------------
    # Decide actions
    # --------------------------------------------------

    def plan(
            self,
            question):


        q = question.lower()


        actions = []



        if any(x in q for x in [

            "login",

            "authentication",

            "auth",

            "password",

            "account"

        ]):


            actions += [

                "search_strings",

                "find_network",

                "find_crypto",

                "trace_calls"

            ]



        elif any(x in q for x in [

            "network",

            "protocol",

            "packet",

            "server"

        ]):


            actions += [

                "find_network",

                "trace_calls"

            ]



        elif any(x in q for x in [

            "crypto",

            "encrypt",

            "decrypt",

            "hash"

        ]):


            actions += [

                "find_crypto",

                "trace_calls"

            ]



        else:


            actions += [

                "general_scan"

            ]



        return actions



    # --------------------------------------------------
    # Execute plan
    # --------------------------------------------------

    def execute(
            self,
            question):


        plan = self.plan(

            question

        )


        result = {


            "question":

                question,


            "created":

                str(

                    datetime.datetime.now()

                ),


            "actions":

                plan

        }



        self.memory.append(

            result

        )


        self.save_memory()



        print()

        print(

            "Investigation plan:"

        )


        for item in plan:


            print(

                " -",

                item

            )



        EvidenceCollector(

            self.export_path

        ).collect()



        ReportGenerator(

            self.export_path

        ).generate()



        print()

        print(

            "[+] Investigation complete"

        )





if __name__ == "__main__":


    if len(sys.argv) < 3:


        print(

            """

Usage:

python agent_controller.py

<export folder>

"question"

"""

        )

        sys.exit(1)



    agent = AgentController(

        sys.argv[1]

    )


    agent.execute(

        sys.argv[2]

    )
