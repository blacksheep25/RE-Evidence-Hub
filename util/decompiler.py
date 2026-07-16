"""
decompiler.py

Wrapper around Ghidra's decompiler.

Responsibilities:

- Initialize decompiler
- Decompile functions
- Return C output
- Return decompiler metadata
- Handle failures cleanly
"""


from ghidra.app.decompiler import DecompInterface
from ghidra.app.decompiler import DecompileOptions



class Decompiler(object):


    def __init__(self, program, timeout=60):

        self.program = program

        self.timeout = timeout

        self.interface = DecompInterface()


        self.initialize()



    # --------------------------------------------------------
    # Initialize Ghidra decompiler
    # --------------------------------------------------------

    def initialize(self):

        options = DecompileOptions()

        self.interface.setOptions(
            options
        )


        success = self.interface.openProgram(
            self.program
        )


        if not success:

            raise RuntimeError(
                "Failed to initialize Ghidra decompiler"
            )



    # --------------------------------------------------------
    # Decompile Function
    # --------------------------------------------------------

    def decompile(self, function, monitor=None):


        result = self.interface.decompileFunction(

            function,

            self.timeout,

            monitor

        )


        if result is None:

            return None



        if not result.decompileCompleted():

            return None



        decompiled = result.getDecompiledFunction()



        if decompiled is None:

            return None



        return decompiled.getC()



    # --------------------------------------------------------
    # Full decompiler information
    # --------------------------------------------------------

    def decompile_info(self, function, monitor=None):


        output = {}


        result = self.interface.decompileFunction(

            function,

            self.timeout,

            monitor

        )


        if result is None:

            output["success"] = False

            return output



        if not result.decompileCompleted():

            output["success"] = False

            output["error"] = result.getErrorMessage()

            return output



        high_function = result.getHighFunction()


        output["success"] = True


        if result.getDecompiledFunction():

            output["c_code"] = (
                result
                .getDecompiledFunction()
                .getC()
            )

        else:

            output["c_code"] = ""



        #
        # Extract local variables
        #

        output["locals"] = []


        if high_function:


            local_symbols = (
                high_function
                .getLocalSymbolMap()
                .getSymbols()
            )


            for symbol in local_symbols:


                output["locals"].append({

                    "name":
                        symbol.getName(),

                    "data_type":
                        str(
                            symbol.getDataType()
                        )

                })


        return output



    # --------------------------------------------------------
    # Dispose
    # --------------------------------------------------------

    def close(self):

        self.interface.dispose()
