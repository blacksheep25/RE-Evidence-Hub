"""
memory_exporter.py

Exports memory block information.

Output:

memory_map.json

Includes:

- Block name
- Start address
- End address
- Size
- Permissions
- Initialization status
- Source information
"""


import os


from util.jsonwriter import JSONWriter



class MemoryExporter(object):


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



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        print(
            "[+] Exporting memory map"
        )


        blocks = []


        iterator = (
            self.memory
            .getBlocks()
        )


        for block in iterator:


            blocks.append(

                self.export_block(
                    block
                )

            )



        path = os.path.join(

            self.output,

            "memory_map.json"

        )


        JSONWriter.save(

            path,

            blocks

        )


        print(

            "[+] Exported {} memory blocks"
            .format(
                len(blocks)
            )

        )



    # --------------------------------------------------------
    # Export block
    # --------------------------------------------------------

    def export_block(
            self,
            block):


        result = {}


        result["name"] = (

            block.getName()

        )


        result["start"] = str(

            block.getStart()

        )


        result["end"] = str(

            block.getEnd()

        )


        result["size"] = (

            block.getSize()

        )


        result["permissions"] = {


            "read":
                block.isRead(),


            "write":
                block.isWrite(),


            "execute":
                block.isExecute()

        }



        result["initialized"] = (

            block.isInitialized()

        )


        result["volatile"] = (

            block.isVolatile()

        )


        result["mapped"] = (

            block.isMapped()

        )


        result["comment"] = (

            block.getComment()

        )



        result["source"] = (

            block.getSourceName()

        )



        return result
