"""
manifest_exporter.py

Creates the master manifest.json file.

Contains:

- Binary information
- Architecture
- Compiler/language metadata
- Memory blocks
- Function statistics
- Export metadata
"""


import os
import datetime


from util.jsonwriter import JSONWriter
from util.filesystem import FileSystem



class ManifestExporter(object):


    VERSION = "1.0.0"



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


        self.memory = (
            program
            .getMemory()
        )


        self.function_manager = (
            program
            .getFunctionManager()
        )



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        manifest = {}


        manifest["exporter"] = {

            "name":
                "Ghidra AI Exporter",

            "version":
                self.VERSION

        }



        manifest["created"] = (
            str(
                datetime.datetime.now()
            )
        )


        manifest["binary"] = (
            self.export_binary_info()
        )


        manifest["functions"] = {

            "count":
                self.function_count()

        }


        manifest["memory"] = (
            self.export_memory()
        )


        manifest["language"] = (
            self.export_language()
        )


        manifest["compiler"] = (
            self.export_compiler()
        )


        path = os.path.join(

            self.output,

            "manifest.json"

        )


        JSONWriter.save(

            path,

            manifest

        )


        print(
            "[+] Manifest written"
        )



    # --------------------------------------------------------
    # Binary information
    # --------------------------------------------------------

    def export_binary_info(self):


        info = {}


        info["name"] = (
            self.program.getName()
        )


        info["domain_file"] = str(

            self.program
            .getDomainFile()

        )


        info["image_base"] = str(

            self.program
            .getImageBase()

        )


        info["executable_format"] = str(

            self.program
            .getExecutableFormat()

        )


        return info


    # --------------------------------------------------------
    # Language information
    # --------------------------------------------------------

    def export_language(self):


        language = (
            self.program
            .getLanguage()
        )


        return {


            "id":
                str(
                    language
                    .getLanguageID()
                ),


            "processor":
                str(
                    language
                    .getProcessor()
                )

        }

    # --------------------------------------------------------
    # Compiler information
    # --------------------------------------------------------

    def export_compiler(self):


        compiler = (
            self.program
            .getCompilerSpec()
        )


        if compiler is None:

            return None


        return {

            "name":
                str(
                    compiler
                )

        }



    # --------------------------------------------------------
    # Memory blocks
    # --------------------------------------------------------

    def export_memory(self):


        blocks = []


        iterator = (
            self.memory
            .getBlocks()
        )


        for block in iterator:


            blocks.append({

                "name":
                    block.getName(),

                "start":
                    str(
                        block
                        .getStart()
                    ),

                "end":
                    str(
                        block
                        .getEnd()
                    ),

                "size":
                    block
                    .getSize(),

                "read":
                    block
                    .isRead(),

                "write":
                    block
                    .isWrite(),

                "execute":
                    block
                    .isExecute(),

                "initialized":
                    block
                    .isInitialized()

            })


        return blocks



    # --------------------------------------------------------
    # Function count
    # --------------------------------------------------------

    def function_count(self):


        count = 0


        iterator = (
            self.function_manager
            .getFunctions(True)
        )


        while iterator.hasNext():

            iterator.next()

            count += 1


        return count
