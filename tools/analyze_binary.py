"""
analyze_binary.py

Master automation runner.

Runs:

1. Vector index creation
2. Automated subsystem analysis
3. Callgraph analysis
4. Startup analysis
5. Evidence collection
6. Final report generation


Usage:

python analyze_binary.py <export folder>
"""


import os
import sys
import time
import traceback



from vector_indexer import VectorIndexer
from analysis_agent import AnalysisAgent
from callgraph_agent import CallgraphAgent
from startup_analyzer import StartupAnalyzer
from evidence_collector import EvidenceCollector
from report_generator import ReportGenerator



class BinaryAnalysisPipeline(object):


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.steps = []



    # --------------------------------------------------------
    # Run step
    # --------------------------------------------------------

    def run_step(
            self,
            name,
            function):


        print()

        print("=" * 60)

        print(

            "[+] {}".format(name)

        )

        print("=" * 60)



        start = time.time()



        try:


            function()



            elapsed = time.time() - start



            self.steps.append({

                "name":

                    name,


                "status":

                    "success",


                "time":

                    elapsed

            })


            print(

                "[+] Completed {:.2f}s".format(

                    elapsed

                )

            )



        except Exception as e:


            elapsed = time.time() - start



            self.steps.append({

                "name":

                    name,


                "status":

                    "failed",


                "error":

                    str(e),


                "time":

                    elapsed

            })


            print(

                "[!] Failed:",

                e

            )


            traceback.print_exc()



    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    def execute(self):


        print()

        print("#" * 60)

        print(" AI Reverse Engineering Pipeline ")

        print("#" * 60)



        self.run_step(

            "Vector Index",

            lambda:

            VectorIndexer(

                self.export_path

            ).build()

        )



        self.run_step(

            "Subsystem Analysis",

            lambda:

            AnalysisAgent(

                self.export_path

            ).analyze()

        )



        self.run_step(

            "Callgraph Intelligence",

            lambda:

            CallgraphAgent(

                self.export_path

            ).analyze()

        )



        self.run_step(

            "Startup Flow",

            lambda:

            StartupAnalyzer(

                self.export_path

            ).analyze()

        )



        self.run_step(

            "Evidence Collection",

            lambda:

            EvidenceCollector(

                self.export_path

            ).collect()

        )



        self.run_step(

            "Final Report",

            lambda:

            ReportGenerator(

                self.export_path

            ).generate()

        )



        self.summary()



    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    def summary(self):


        print()

        print("#" * 60)

        print(" Analysis Complete ")

        print("#" * 60)



        for step in self.steps:


            if step["status"] == "success":


                print(

                    "[OK] {} ({:.2f}s)".format(

                        step["name"],

                        step["time"]

                    )

                )


            else:


                print(

                    "[FAILED] {}".format(

                        step["name"]

                    )

                )



        print()

        print(

            "Output:"

        )

        print(

            self.export_path

        )





if __name__ == "__main__":


    if len(sys.argv) != 2:


        print(

            "Usage: python analyze_binary.py <export folder>"

        )


        sys.exit(1)



    pipeline = BinaryAnalysisPipeline(

        sys.argv[1]

    )


    pipeline.execute()
