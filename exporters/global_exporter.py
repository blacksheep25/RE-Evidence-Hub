"""
global_exporter.py

Exports global variables and references.

Output:

globals.json

Includes:

- Address
- Name
- Data type
- Size
- Value
- Read references
- Write references
- Functions using the global
"""


import os


from util.jsonwriter import JSONWriter



class GlobalExporter(object):


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


        self.symbol_table = (
            program
            .getSymbolTable()
        )



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        print(
            "[+] Exporting globals"
        )


        globals = []


        data_iterator = (
            self.listing
            .getDefinedData(True)
        )


        while data_iterator.hasNext():


            data = data_iterator.next()


            if self.is_global(data):


                globals.append(

                    self.export_global(
                        data
                    )

                )



        path = os.path.join(

            self.output,

            "globals.json"

        )


        JSONWriter.save(

            path,

            globals

        )


        print(

            "[+] Exported {} globals"
            .format(
                len(globals)
            )

        )



    # --------------------------------------------------------
    # Determine global data
    # --------------------------------------------------------

    def is_global(
            self,
            data):


        address = (
            data.getAddress()
        )


        block = (
            self.program
            .getMemory()
            .getBlock(address)
        )


        if block is None:

            return False


        name = (
            block.getName()
        )


        #
        # Ignore code sections
        #

        if name == ".text":

            return False


        return True



    # --------------------------------------------------------
    # Export global
    # --------------------------------------------------------

    def export_global(
            self,
            data):


        result = {}


        result["address"] = str(

            data.getAddress()

        )


        result["name"] = (

            self.get_symbol_name(
                data
            )

        )


        result["datatype"] = str(

            data.getDataType()

        )


        result["size"] = (

            data.getLength()

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
    # Symbol name
    # --------------------------------------------------------

    def get_symbol_name(
            self,
            data):


        symbols = (
            self.symbol_table
            .getSymbols(
                data.getAddress()
            )
        )


        for symbol in symbols:


            return symbol.getName()


        return ""



    # --------------------------------------------------------
    # References
    # --------------------------------------------------------

    def get_references(
            self,
            data):


        result = []


        refs = (
            self.reference_manager
            .getReferencesTo(
                data.getAddress()
            )
        )


        while refs.hasNext():


            ref = refs.next()


            result.append({

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


        return result



    # --------------------------------------------------------
    # Functions using global
    # --------------------------------------------------------

    def get_functions(
            self,
            data):


        result = []


        refs = (
            self.reference_manager
            .getReferencesTo(
                data.getAddress()
            )
        )


        while refs.hasNext():


            ref = refs.next()


            function = (
                self.function_manager
                .getFunctionContaining(
                    ref.getFromAddress()
                )
            )


            if function:


                result.append({

                    "name":
                        function.getName(),

                    "address":
                        str(
                            function
                            .getEntryPoint()
                        )

                })


        return self.unique(
            result
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
