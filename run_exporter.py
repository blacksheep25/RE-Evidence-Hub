"""
run_exporter.py

Main Ghidra Script Manager entry point.
"""


import traceback
import sys
import os


SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


if SCRIPT_DIR not in sys.path:

    sys.path.append(
        SCRIPT_DIR
    )



from AIExporter import AIExporter



class ExportRunner(object):


    def run(self):


        print("")
        print("==============================")
        print(" Ghidra AI Exporter")
        print("==============================")
        print("")


        try:


            program = currentProgram


            if program is None:


                print(
                    "[!] No program loaded"
                )

                return



            print(

                "[+] Program: {}".format(

                    program.getName()

                )

            )


            exporter = AIExporter(

                program,

                monitor

            )


            exporter.run()



            print("")
            print(
                "[+] Export finished"
            )



        except Exception as e:


            print("")
            print(
                "[!] Export failed"
            )

            print(
                str(e)
            )


            traceback.print_exc()



ExportRunner().run()
