"""
ai_summary_exporter.py

Creates AI-friendly Markdown summaries
from exported function JSON files.

Input:

functions/*.json

Output:

markdown/*.md
"""


import os
import json


from util.filesystem import FileSystem



class AISummaryExporter(object):


    def __init__(
            self,
            program=None,
            monitor=None,
            output=None,
            config=None):

        self.program = program
        self.monitor = monitor
        self.output = output
        self.config = config


        self.function_directory = os.path.join(

            output,

            "functions"

        )


        self.markdown_directory = os.path.join(

            output,

            "markdown"

        )


        FileSystem.ensure_directory(

            self.markdown_directory

        )



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        print(
            "[+] Creating AI summaries"
        )


        count = 0


        files = os.listdir(

            self.function_directory

        )


        for filename in files:


            if not filename.endswith(
                ".json"
            ):

                continue


            path = os.path.join(

                self.function_directory,

                filename

            )


            with open(
                path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                function = json.load(f)



            markdown = (
                self.create_summary(
                    function
                )
            )


            output_file = os.path.join(

                self.markdown_directory,

                filename.replace(
                    ".json",
                    ".md"
                )

            )


            FileSystem.write_text(

                output_file,

                markdown

            )


            count += 1



        print(

            "[+] Created {} summaries"
            .format(
                count
            )

        )



    # --------------------------------------------------------
    # Build markdown
    # --------------------------------------------------------

    def create_summary(
            self,
            function):


        text = []


        text.append(

            "# {}".format(

                function.get(
                    "name",
                    ""
                )

            )

        )


        text.append("")


        text.append(

            "## Address"

        )


        text.append(

            function.get(
                "address",
                ""
            )

        )


        text.append("")


        text.append(

            "## Signature"

        )


        text.append(

            function.get(
                "signature",
                ""
            )

        )


        text.append("")


        text.append(

            "## Size"

        )


        text.append(

            str(
                function.get(
                    "size",
                    0
                )
            )

        )


        text.append("")


        text.append(

            "## Calls"

        )


        for call in function.get(
            "calls",
            []
        ):


            text.append(

                "- {} ({})".format(

                    call.get(
                        "name",
                        ""
                    ),

                    call.get(
                        "address",
                        ""
                    )

                )

            )


        text.append("")


        text.append(

            "## Called By"

        )


        for caller in function.get(
            "called_by",
            []
        ):


            text.append(

                "- {} ({})".format(

                    caller.get(
                        "name",
                        ""
                    ),

                    caller.get(
                        "address",
                        ""
                    )

                )

            )


        text.append("")


        text.append(

            "## Assembly"

        )


        text.append(

            "```asm"

        )


        text.append(

            function.get(
                "assembly",
                ""
            )

        )


        text.append(

            "```"

        )


        text.append("")


        text.append(

            "## Decompiled Code"

        )


        text.append(

            "```c"

        )


        decompiler = function.get(

            "decompiler",

            {}

        )


        text.append(

            decompiler.get(
                "c_code",
                ""
            )

        )


        text.append(

            "```"

        )


        return "\n".join(text)
