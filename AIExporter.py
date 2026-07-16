"""
AIExporter.py

Main exporter controller.
"""


from pipeline import ExportPipeline
from config import Config



class AIExporter(object):


    def __init__(
            self,
            program,
            monitor):


        self.program = program

        self.monitor = monitor

        self.config = Config()



    def run(self):


        output = (

            self.config
            .get_output_directory(
                self.program
            )

        )


        pipeline = ExportPipeline(

            self.program,

            self.monitor,

            output,

            self.config

        )


        pipeline.run()
