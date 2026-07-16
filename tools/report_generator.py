"""
report_generator.py

Generates analyst-style reverse engineering reports.

Outputs:

reverse_engineering_report.md
reverse_engineering_report.json
"""


import os
import json
import datetime



class ReportGenerator:


    def __init__(
            self,
            export_path):


        self.export_path = export_path


        self.data = {}


        self.load()



    # -------------------------------------------------
    # Load evidence
    # -------------------------------------------------

    def load(self):


        files = {


            "manifest":

                "manifest.json",


            "triage":

                "triage_report.json",


            "memory":

                "investigation_memory.json",


            "startup":

                "startup_analysis.json"

        }



        for key,file in files.items():


            path = os.path.join(

                self.export_path,

                file

            )


            if os.path.exists(path):


                with open(

                    path,

                    "r",

                    encoding="utf-8"

                ) as f:


                    self.data[key] = json.load(f)


            else:


                self.data[key] = {}



    # -------------------------------------------------
    # Generate JSON
    # -------------------------------------------------

    def build_report(self):


        manifest = self.data.get(

            "manifest",

            {}

        )


        triage = self.data.get(

            "triage",

            {}

        )


        memory = self.data.get(

            "memory",

            {}

        )


        return {


            "generated":

                str(

                    datetime.datetime.now()

                ),



            "binary":

                manifest.get(

                    "binary",

                    {}

                ),



            "architecture":

                {


                    "language":

                        manifest.get(

                            "language",

                            {}

                        ),


                    "compiler":

                        manifest.get(

                            "compiler",

                            {}

                        )

                },



            "subsystems":

                triage.get(

                    "subsystems",

                    []

                ),



            "priority_functions":

                triage.get(

                    "priority_functions",

                    []

                ),



            "findings":

                memory.get(

                    "findings",

                    []

                ),



            "hypotheses":

                memory.get(

                    "hypotheses",

                    []

                ),



            "recommended_actions":

                triage.get(

                    "recommended_tasks",

                    []

                )

        }



    # -------------------------------------------------
    # Markdown generation
    # -------------------------------------------------

    def markdown(
            self,
            report):


        lines = []



        lines.append(

            "# Reverse Engineering Report"

        )


        lines.append("")



        lines.append(

            "Generated: {}".format(

                report["generated"]

            )

        )


        lines.append("")



        # Binary

        lines.append(

            "## Binary Overview"

        )


        binary = report["binary"]


        for key,value in binary.items():


            lines.append(

                "- **{}**: {}".format(

                    key,

                    value

                )

            )


        lines.append("")



        # Architecture

        lines.append(

            "## Architecture"

        )


        lines.append(

            json.dumps(

                report["architecture"],

                indent=2

            )

        )


        lines.append("")



        # Subsystems

        lines.append(

            "## Detected Subsystems"

        )


        for subsystem in report["subsystems"]:


            lines.append(

                "- {}".format(

                    subsystem.get(

                        "subsystem",

                        "unknown"

                    )

                )

            )


            for indicator in subsystem.get(

                "indicators",

                []

            ):


                lines.append(

                    "  - {}".format(

                        indicator

                    )

                )


        lines.append("")



        # Functions

        lines.append(

            "## Priority Functions"

        )


        for function in report["priority_functions"]:


            lines.append(

                "- {} @ {}"

                .format(

                    function.get(

                        "name"

                    ),

                    function.get(

                        "address"

                    )

                )

            )


        lines.append("")



        # Findings

        lines.append(

            "## Findings"

        )


        for finding in report["findings"]:


            lines.append(

                "### {}".format(

                    finding.get(

                        "title",

                        "Unknown"

                    )

                )

            )


            lines.append(

                finding.get(

                    "description",

                    ""

                )

            )


            lines.append(

                "Confidence: {}".format(

                    finding.get(

                        "confidence",

                        "unknown"

                    )

                )

            )


            lines.append("")



        # Hypotheses

        lines.append(

            "## Open Hypotheses"

        )


        for item in report["hypotheses"]:


            lines.append(

                "- {} ({})"

                .format(

                    item.get(

                        "statement"

                    ),

                    item.get(

                        "status"

                    )

                )

            )


        return "\n".join(lines)



    # -------------------------------------------------
    # Write
    # -------------------------------------------------

    def generate(self):


        report = self.build_report()



        json_file = os.path.join(

            self.export_path,

            "reverse_engineering_report.json"

        )


        with open(

            json_file,

            "w",

            encoding="utf-8"

        ) as f:


            json.dump(

                report,

                f,

                indent=2

            )



        md_file = os.path.join(

            self.export_path,

            "reverse_engineering_report.md"

        )


        with open(

            md_file,

            "w",

            encoding="utf-8"

        ) as f:


            f.write(

                self.markdown(

                    report

                )

            )



        print(

            "[+] Reports generated"

        )





if __name__ == "__main__":


    import sys


    if len(sys.argv) != 2:


        print(

            "Usage: python report_generator.py <export folder>"

        )


        exit(1)



    ReportGenerator(

        sys.argv[1]

    ).generate()
