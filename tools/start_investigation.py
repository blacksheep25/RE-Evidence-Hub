"""
start_investigation.py

Master reverse engineering launcher.

Runs:

1. Binary triage
2. Evidence collection
3. Startup analysis
4. Report generation
5. Investigation memory initialization

Then launches AI assistant.

Usage:

python start_investigation.py <export folder>
"""


import os
import sys
import time
import traceback


# Make the sibling tools importable whether this file is run as a script
# (python tools/start_investigation.py) or imported as tools.start_investigation.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


from tools.binary_triage import BinaryTriage
from tools.evidence_collector import EvidenceCollector
from tools.startup_analyzer import StartupAnalyzer
from tools.report_generator import ReportGenerator
from tools.investigation_memory import InvestigationMemory



class InvestigationRunner:


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.results = []



    # -------------------------------------------------
    # Run task
    # -------------------------------------------------

    def run(
            self,
            name,
            task):


        print()

        print("=" * 60)

        print(

            "[+] {}".format(name)

        )

        print("=" * 60)



        start = time.time()


        try:


            task()


            elapsed = time.time() - start


            self.results.append({

                "task":

                    name,


                "status":

                    "complete",


                "time":

                    elapsed

            })


            print(

                "[OK] {:.2f}s".format(

                    elapsed

                )

            )



        except Exception as e:


            elapsed = time.time() - start


            self.results.append({

                "task":

                    name,


                "status":

                    "failed",


                "error":

                    str(e)

            })


            print(

                "[FAILED]",

                e

            )


            traceback.print_exc()



    # -------------------------------------------------
    # Execute
    # -------------------------------------------------

    def execute(self):


        print()

        print("#" * 60)

        print(" AI Reverse Engineering Investigation ")

        print("#" * 60)



        self.run(

            "Binary Triage",

            lambda:

            BinaryTriage(

                self.export_path

            ).generate()

        )



        self.run(

            "Evidence Database",

            lambda:

            EvidenceCollector(

                self.export_path

            ).collect()

        )



        self.run(

            "Startup Analysis",

            lambda:

            StartupAnalyzer(

                self.export_path

            ).analyze()

        )



        self.run(

            "Report Generation",

            lambda:

            ReportGenerator(

                self.export_path

            ).generate()

        )



        self.run(

            "Initialize Investigation Memory",

            lambda:

            InvestigationMemory(

                self.export_path

            ).save()

        )



        self.write_session()



    # -------------------------------------------------
    # Save session info
    # -------------------------------------------------

    def write_session(self):


        import json



        path = os.path.join(

            self.export_path,

            "investigation_session.json"

        )



        with open(

            path,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                {

                    "pipeline":

                        self.results

                },

                f,

                indent=2

            )



        print()

        print("#" * 60)

        print(" Investigation Ready ")

        print("#" * 60)

        print()

        print(

            "Next step: start tools/tool_agent.py"

        )





if __name__ == "__main__":


    if len(sys.argv) != 2:


        print(

            "Usage: python start_investigation.py <export folder>"

        )

        sys.exit(1)



    runner = InvestigationRunner(

        sys.argv[1]

    )


    runner.execute()
