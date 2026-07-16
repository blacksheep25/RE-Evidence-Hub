"""
config.py

Central configuration for the Ghidra AI exporter.

Controls:

- Output location
- Export modules
- Decompiler settings
- AI preparation options
"""


import os

OUTPUT_PATH = r"%USERPROFILE%\ghidra_ai_exports\sample_program.exe"

class Config(object):


    VERSION = "1.0.0"



    def __init__(self):


        #
        # General
        #

        self.exporter_name = (
            "Ghidra AI Exporter"
        )


        #
        # Output
        #

        self.output_root = (

            os.path.expanduser(
                "~/ghidra_ai_exports"
            )

        )



        #
        # Decompiler
        #

        self.export_decompiler = True


        self.decompiler_timeout = 120



        #
        # Core exporters
        #

        self.export_memory = True

        self.export_imports = True

        self.export_types = True

        self.export_globals = True

        self.export_strings = True

        self.export_callgraph = True

        # Hybrid retrieval

        USE_FUNCTION_RANKER = True

        # Number of retrieved candidates sent to reranker
        RANK_LIMIT = 5000

        # Save rank diagnostics
        SAVE_RANK_RESULTS = False

        #
        # Function exporter
        #

        self.export_xrefs = True

        self.export_comments = True



        #
        # AI processing
        #

        self.export_ai_summaries = True


        self.create_search_index = True


        self.export_ai_context = True


        self.export_function_summaries = True



        #
        # Future modules
        #

        self.export_entropy = False

        self.export_embeddings = False



    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    def get_output_directory(
            self,
            program):


        name = (

            program
            .getName()

        )


        safe_name = (

            name
            .replace(
                " ",
                "_"
            )

        )


        path = os.path.join(

            self.output_root,

            safe_name

        )


        if not os.path.exists(path):

            os.makedirs(path)



        return path



    # --------------------------------------------------------
    # Display configuration
    # --------------------------------------------------------

    def dump(self):


        return {


            "version":
                self.VERSION,


            "decompiler":
                self.export_decompiler,


            "memory":
                self.export_memory,


            "imports":
                self.export_imports,


            "types":
                self.export_types,


            "globals":
                self.export_globals,


            "strings":
                self.export_strings,


            "callgraph":
                self.export_callgraph,


            "ai_summaries":
                self.export_ai_summaries,


            "search_index":
                self.create_search_index,


            "ai_context":
                self.export_ai_context,


            "function_summaries":
                self.export_function_summaries,


            "embeddings":
                self.export_embeddings

        }
