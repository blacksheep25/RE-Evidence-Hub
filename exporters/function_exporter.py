"""
function_exporter.py

Exports every function in the binary.

Exports:

- Name
- Address
- Namespace
- Size
- Signature
- Parameters
- Return type
- Local variables
- Decompiled C
- Assembly
- Calls made
- Callers
- Xrefs
- Comments
- Hashes

Output:

functions/
    FUNCTION_ADDRESS.json
"""


import hashlib
import os


from ghidra.program.model.symbol import RefType


from util.decompiler import Decompiler
from util.jsonwriter import JSONWriter
from util.ghidrautils import GhidraUtils



class FunctionExporter(object):


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


        self.function_manager = (
            program
            .getFunctionManager()
        )


        self.reference_manager = (
            program
            .getReferenceManager()
        )


        self.listing = (
            program
            .getListing()
        )


        self.decompiler = Decompiler(

            program,

            config.decompiler_timeout

        )


        self.output_dir = os.path.join(

            output,

            "functions"

        )


        if not os.path.exists(
            self.output_dir
        ):

            os.makedirs(
                self.output_dir
            )



    # --------------------------------------------------------
    # Export all functions
    # --------------------------------------------------------

    def export(self):


        iterator = (
            self.function_manager
            .getFunctions(True)
        )


        count = 0


        for function in iterator:


            count += 1


            print(
                "[FUNCTION {0}] {1}".format(
                    count,
                    function.getName()
                )
            )


            try:

                self.export_function(
                    function
                )


            except Exception as e:


                print(
                    "Failed exporting {0}: {1}"
                    .format(
                        function.getName(),
                        e
                    )
                )



    # --------------------------------------------------------
    # Export single function
    # --------------------------------------------------------

    def export_function(
            self,
            function):


        data = {}


        address = str(
            function.getEntryPoint()
        )


        data["address"] = address


        data["name"] = (
            function
            .getName()
        )


        data["namespace"] = (
            GhidraUtils
            .get_namespace(function)
        )


        data["external"] = (
            function
            .isExternal()
        )


        data["range"] = (
            GhidraUtils
            .get_function_range(function)
        )


        data["size"] = (
            GhidraUtils
            .get_function_size(function)
        )


        data["signature"] = str(

            function
            .getSignature()

        )


        data["return_type"] = str(

            function
            .getReturnType()

        )


        data["parameters"] = (
            self.export_parameters(function)
        )


        data["locals"] = (
            self.export_locals(function)
        )


        data["assembly"] = (
            self.export_assembly(function)
        )


        if self.config.export_decompiler:

            result = (
                self.decompiler
                .decompile_info(
                    function,
                    self.monitor
                )
            )


            data["decompiler"] = result


        else:

            data["decompiler"] = None



        data["calls"] = (
            self.export_calls(function)
        )


        data["called_by"] = (
            self.export_callers(function)
        )


        if self.config.export_xrefs:

            data["xrefs"] = (
                self.export_xrefs(function)
            )


        else:

            data["xrefs"] = []



        if self.config.export_comments:

            data["comments"] = (
                self.export_comments(function)
            )


        else:

            data["comments"] = []



        data["instruction_count"] = (
            self.instruction_count(function)
        )


        data["hash"] = (
            self.hash_text(
                data["assembly"]
            )
        )



        filename = os.path.join(

            self.output_dir,

            address + ".json"

        )


        JSONWriter.save(

            filename,

            data

        )

        print(
            "[+] Written {}".format(filename)
        )


    # --------------------------------------------------------
    # Parameters
    # --------------------------------------------------------

    def export_parameters(
            self,
            function):


        result = []


        for parameter in function.getParameters():


            result.append({

                "name":
                    parameter.getName(),

                "datatype":
                    str(
                        parameter
                        .getDataType()
                    ),

                "ordinal":
                    parameter.getOrdinal()

            })


        return result



    # --------------------------------------------------------
    # Local variables
    # --------------------------------------------------------

    def export_locals(
            self,
            function):


        result = []


        for variable in function.getLocalVariables():


            result.append({

                "name":
                    variable.getName(),

                "datatype":
                    str(
                        variable
                        .getDataType()
                    ),

                "length":
                    variable.getLength()

            })


        return result



    # --------------------------------------------------------
    # Assembly
    # --------------------------------------------------------

    def export_assembly(
            self,
            function):


        output = []


        instructions = (
            self.listing
            .getInstructions(
                function.getBody(),
                True
            )
        )


        for instruction in instructions:


            output.append(

                "{} : {}".format(

                    instruction.getAddress(),

                    instruction.toString()

                )

            )


        return "\n".join(output)



    # --------------------------------------------------------
    # Functions called
    # --------------------------------------------------------

    def export_calls(
            self,
            function):


        calls = []


        instructions = (
            self.listing
            .getInstructions(
                function.getBody(),
                True
            )
        )


        for instruction in instructions:


            flows = (
                instruction.getFlows()
            )


            for flow in flows:


                target = (
                    self.function_manager
                    .getFunctionAt(flow)
                )


                if target:


                    calls.append({

                        "name":
                            target.getName(),

                        "address":
                            str(
                                target
                                .getEntryPoint()
                            ),

                        "external":
                            target
                            .isExternal()

                    })


        return self.unique(calls)



    # --------------------------------------------------------
    # Callers
    # --------------------------------------------------------

    def export_callers(
            self,
            function):


        result = []


        refs = (
            self.reference_manager
            .getReferencesTo(
                function.getEntryPoint()
            )
        )


        for ref in refs:


            if ref.getReferenceType().isCall():


                caller = (
                    self.function_manager
                    .getFunctionContaining(
                        ref.getFromAddress()
                    )
                )


                if caller:


                    result.append({

                        "name":
                            caller.getName(),

                        "address":
                            str(
                                caller
                                .getEntryPoint()
                            )

                    })


        return self.unique(result)



    # --------------------------------------------------------
    # Cross references
    # --------------------------------------------------------

    def export_xrefs(
            self,
            function):


        result = []


        refs = (
            self.reference_manager
            .getReferencesTo(
                function.getEntryPoint()
            )
        )


        for ref in refs:


            result.append({

                "from":
                    str(
                        ref.getFromAddress()
                    ),

                "type":
                    str(
                        ref.getReferenceType()
                    )

            })


        return result



    # --------------------------------------------------------
    # Comments
    # --------------------------------------------------------

    def export_comments(
            self,
            function):


        comments = []


        instructions = (
            self.listing
            .getInstructions(
                function.getBody(),
                True
            )
        )


        for instruction in instructions:


            comment = (
                self.listing
                .getComment(
                    0,
                    instruction.getAddress()
                )
            )


            if comment:


                comments.append({

                    "address":
                        str(
                            instruction
                            .getAddress()
                        ),

                    "text":
                        comment

                })


        return comments



    # --------------------------------------------------------
    # Instruction count
    # --------------------------------------------------------

    def instruction_count(
            self,
            function):


        count = 0


        instructions = (
            self.listing
            .getInstructions(
                function.getBody(),
                True
            )
        )


        for instruction in instructions:

            count += 1


        return count



    # --------------------------------------------------------
    # Hash
    # --------------------------------------------------------

    def hash_text(
            self,
            text):


        return hashlib.sha256(

            text.encode(
                "utf-8"
            )

        ).hexdigest()



    # --------------------------------------------------------
    # Remove duplicate dictionaries
    # --------------------------------------------------------

    def unique(
            self,
            items):


        output = []

        seen = set()


        for item in items:


            key = str(item)


            if key not in seen:


                seen.add(key)

                output.append(item)


        return output
