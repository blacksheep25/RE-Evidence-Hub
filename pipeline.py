"""
pipeline.py

Controls execution of all exporters.

Runs:

- Manifest
- Memory
- Imports
- Datatypes
- Globals
- Strings
- Functions
- Callgraph
- AI summaries
- Search index
"""


import time
import traceback



from exporters.manifest_exporter import ManifestExporter
from exporters.memory_exporter import MemoryExporter
from exporters.import_exporter import ImportExporter
from exporters.datatype_exporter import DataTypeExporter
from exporters.global_exporter import GlobalExporter
from exporters.string_exporter import StringExporter
from exporters.function_exporter import FunctionExporter
from exporters.callgraph_exporter import CallGraphExporter
from exporters.ai_summary_exporter import AISummaryExporter
from exporters.search_index_exporter import SearchIndexExporter
from exporters.ai_context_exporter import AIContextExporter
from exporters.function_summary_exporter import FunctionSummaryExporter
from exporters.embedding_exporter import EmbeddingExporter



class ExportPipeline(object):


    def __init__(
            self,
            program,
            monitor,
            output,
            config):


        self.program = program

        self.monitor = monitor

        self.output = output

        self.config = config


        self.results = []



    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    def run(self):


        print("")
        print("==============================")
        print(" Ghidra AI Export Pipeline")
        print("==============================")
        print("")



        exporters = [

            (
                "Manifest",
                ManifestExporter,
                True
            ),


            (
                "Memory",
                MemoryExporter,
                self.config.export_memory
            ),


            (
                "Imports",
                ImportExporter,
                self.config.export_imports
            ),


            (
                "Datatypes",
                DataTypeExporter,
                self.config.export_types
            ),


            (
                "Globals",
                GlobalExporter,
                self.config.export_globals
            ),


            (
                "Strings",
                StringExporter,
                self.config.export_strings
            ),


            (
                "Functions",
                FunctionExporter,
                True
            ),


            (
                "Callgraph",
                CallGraphExporter,
                self.config.export_callgraph
            )

        ]



        for name, exporter, enabled in exporters:


            if not enabled:

                continue


            self.execute(

                name,

                exporter

            )



        #
        # Post-processing exporters
        #

        self.execute(

            "AI summaries",

            AISummaryExporter,

            self.config.export_ai_summaries

        )



        self.execute(

            "Search index",

            SearchIndexExporter,

            self.config.create_search_index

        )

        self.execute(

            "AI Context",

            AIContextExporter,

            self.config.export_ai_context

        )


        self.execute(

            "Function summaries",

            FunctionSummaryExporter,

            self.config.export_function_summaries

        )


        self.execute(

            "AI chunks",

            EmbeddingExporter,

            self.config.export_embeddings

        )


        self.write_report()



    # --------------------------------------------------------
    # Execute exporter safely
    # --------------------------------------------------------

    def execute(
            self,
            name,
            exporter,
            enabled=True):


        if not enabled:


            return


        print("")
        print(
            "[+] {}".format(name)
        )


        start = time.time()


        try:


            #
            # Different exporters
            # have different constructors
            #


            instance = exporter(
                self.program,
                self.monitor,
                self.output,
                self.config
            )



            instance.export()



            elapsed = (
                time.time()
                -
                start
            )


            self.results.append({

                "name":
                    name,

                "success":
                    True,

                "time":
                    elapsed

            })



        except Exception as e:


            print(
                "[!] {} failed"
                .format(name)
            )


            traceback.print_exc()


            self.results.append({

                "name":
                    name,

                "success":
                    False,

                "error":
                    str(e)

            })



    # --------------------------------------------------------
    # Export report
    # --------------------------------------------------------

    def write_report(self):


        import json
        import os



        report = {

            "pipeline":
                "completed" if all(
                    item.get("success")
                    for item in self.results
                ) else "completed_with_errors",


            "config":
                self.config.dump(),

            "results":
                self.results

        }



        path = os.path.join(

            self.output,

            "export_report.json"

        )


        with open(
            path,
            "w"
        ) as f:


            json.dump(

                report,

                f,

                indent=4

            )


        print("")
        print("==============================")
        print(" Export complete")
        print("==============================")
