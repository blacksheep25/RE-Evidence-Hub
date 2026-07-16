"""
import_exporter.py

Exports imported and exported functions.

Output:

imports.json
exports.json

Includes:

- Library name
- Function name
- Address
- Calling functions
- External status
"""


import os


from util.jsonwriter import JSONWriter



class ImportExporter(object):


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


        self.symbol_table = (
            program
            .getSymbolTable()
        )


        self.function_manager = (
            program
            .getFunctionManager()
        )


        self.reference_manager = (
            program
            .getReferenceManager()
        )



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        self.export_imports()

        self.export_exports()



    # --------------------------------------------------------
    # Imports
    # --------------------------------------------------------

    def export_imports(self):


        imports = []


        functions = (
            self.function_manager
            .getExternalFunctions()
        )


        iterator = functions.iterator()



        while iterator.hasNext():


            function = iterator.next()


            entry = {}


            entry["name"] = (
                function.getName()
            )


            entry["address"] = (
                str(
                    function
                    .getEntryPoint()
                )
            )


            namespace = (
                function
                .getParentNamespace()
            )


            if namespace:

                entry["library"] = (
                    namespace.getName()
                )

            else:

                entry["library"] = ""



            entry["references"] = (
                self.get_callers(function)
            )


            imports.append(
                entry
            )



        path = os.path.join(

            self.output,

            "imports.json"

        )


        JSONWriter.save(

            path,

            imports

        )


        print(

            "[+] Exported {} imports"
            .format(
                len(imports)
            )

        )



    # --------------------------------------------------------
    # Exports
    # --------------------------------------------------------

    def export_exports(self):


        exports = []


        symbols = (
            self.symbol_table
            .getAllSymbols(True)
        )


        while symbols.hasNext():


            symbol = symbols.next()


            if symbol.isExternalEntryPoint():


                exports.append({

                    "name":
                        symbol.getName(),

                    "address":
                        str(
                            symbol
                            .getAddress()
                        )

                })



        path = os.path.join(

            self.output,

            "exports.json"

        )


        JSONWriter.save(

            path,

            exports

        )


        print(

            "[+] Exported {} exports"
            .format(
                len(exports)
            )

        )



    # --------------------------------------------------------
    # Functions calling imported API
    # --------------------------------------------------------

    def get_callers(
            self,
            function):


        result = []


        refs = (
            self.reference_manager
            .getReferencesTo(
                function
                .getEntryPoint()
            )
        )


        while refs.hasNext():


            ref = refs.next()


            caller = (
                self.function_manager
                .getFunctionContaining(
                    ref
                    .getFromAddress()
                )
            )


            if caller:


                result.append({

                    "name":
                        caller
                        .getName(),

                    "address":
                        str(
                            caller
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
