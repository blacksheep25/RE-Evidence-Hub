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


    VERSION = "1.1.0"



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


        # Keep the project-domain identity for consumers of manifest 1.0 while
        # also recording the original input path used for provenance.
        info["domain_file"] = str(

            self.program
            .getDomainFile()

        )


        info["source_path"] = str(

            self.program
            .getExecutablePath()

        )


        info["image_base"] = str(

            self.program
            .getImageBase()

        )


        info["executable_format"] = str(

            self.program
            .getExecutableFormat()

        )


        #
        # Input-file hashes Ghidra computed at import. These tie an export to a
        # specific binary (chain of custody) and are the input file's own
        # digests, not hashes of the export.
        #

        md5 = self.program.getExecutableMD5()

        if md5:

            info["md5"] = str(md5)


        sha256 = self.executable_sha256()

        if sha256:

            info["sha256"] = str(sha256)


        return info


    def executable_sha256(self):

        #
        # getExecutableSHA256 exists in modern Ghidra; guard older builds so a
        # missing getter degrades to "no sha256" rather than aborting.
        #

        try:

            return (
                self.program
                .getExecutableSHA256()
            )

        except Exception:

            return None


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

            # ``name`` is retained for manifest 1.0 consumers. It may contain
            # Ghidra's Java representation; new consumers should use ``id``.
            "name":
                str(
                    compiler
                ),


            "id":
                str(
                    compiler
                    .getCompilerSpecID()
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
