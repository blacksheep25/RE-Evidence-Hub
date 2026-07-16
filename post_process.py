import os

from exporters.ai_summary_exporter import AISummaryExporter
from exporters.search_index_exporter import SearchIndexExporter
from exporters.function_summary_exporter import FunctionSummaryExporter


import sys

EXPORT_PATH = sys.argv[1]


def run():

    print("==============================")
    print(" Ghidra AI Post Processor")
    print("==============================")


    jobs = [

        (
            "AI summaries",
            AISummaryExporter
        ),

        (
            "Search index",
            SearchIndexExporter
        ),

        (
            "Function summaries",
            FunctionSummaryExporter
        )

    ]


    for name, exporter in jobs:

        print("")
        print("[+] " + name)

        try:

            instance = exporter(
                program=None,
                monitor=None,
                output=EXPORT_PATH,
                config=None
            )

            instance.export()

            print("[+] Complete")

        except Exception as e:

            print("[!] Failed")
            print(e)



if __name__ == "__main__":

    run()
