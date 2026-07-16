"""
string_exporter.py

Exports strings from the binary.

Output:

strings.json

Each entry contains:

- Address
- Value
- Length
- Datatype
- References
- Functions referencing the string
"""


import os


from ghidra.program.model.data import StringDataType


from util.jsonwriter import JSONWriter



class StringExporter(object):


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


        self.listing = (
            program
            .getListing()
        )


        self.reference_manager = (
            program
            .getReferenceManager()
        )


        self.function_manager = (
            program
            .getFunctionManager()
        )



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        print(
            "[+] Exporting strings"
        )


        strings = []


        data_iterator = (
            self.listing
            .getDefinedData(True)
        )


        while data_iterator.hasNext():


            data = data_iterator.next()


            if self.is_string(data):


                entry = (
                    self.export_string(data)
                )


                strings.append(
                    entry
                )



        path = os.path.join(

            self.output,

            "strings.json"

        )


        JSONWriter.save(

            path,

            strings

        )


        print(

            "[+] Exported {} strings"
            .format(
                len(strings)
            )

        )



    # --------------------------------------------------------
    # Check if data is string
    # --------------------------------------------------------

    def is_string(self, data):


        datatype = (
            data.getDataType()
        )


        return isinstance(

            datatype,

            StringDataType

        )



    # --------------------------------------------------------
    # Export string
    # --------------------------------------------------------

    def export_string(
            self,
            data):


        result = {}


        result["address"] = str(

            data.getAddress()

        )


        result["length"] = (

            data.getLength()

        )


        result["datatype"] = str(

            data.getDataType()

        )


        try:

            result["value"] = str(

                data.getValue()

            )

        except:


            result["value"] = ""



        result["references"] = (

            self.get_references(
                data
            )

        )


        result["functions"] = (

            self.get_functions(
                data
            )

        )


        return result



    # --------------------------------------------------------
    # References to string
    # --------------------------------------------------------

    def get_references(
            self,
            data):


        refs = []


        iterator = (
            self.reference_manager
            .getReferencesTo(
                data.getAddress()
            )
        )


        while iterator.hasNext():


            ref = iterator.next()


            refs.append({

                "from":
                    str(
                        ref
                        .getFromAddress()
                    ),

                "type":
                    str(
                        ref
                        .getReferenceType()
                    )

            })


        return refs



    # --------------------------------------------------------
    # Functions using string
    # --------------------------------------------------------

    def get_functions(
            self,
            data):


        functions = []


        iterator = (
            self.reference_manager
            .getReferencesTo(
                data.getAddress()
            )
        )


        while iterator.hasNext():


            ref = iterator.next()


            function = (
                self.function_manager
                .getFunctionContaining(
                    ref.getFromAddress()
                )
            )


            if function:


                functions.append({

                    "name":
                        function
                        .getName(),

                    "address":
                        str(
                            function
                            .getEntryPoint()
                        )

                })


        return self.unique(
            functions
        )



    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    def unique(
            self,
            items):


        result = []

        seen = set()


        for item in items:


            key = str(item)


            if key not in seen:

                seen.add(key)

                result.append(
                    item
                )


        return result
