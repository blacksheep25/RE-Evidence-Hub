"""
ghidrautils.py

Common Ghidra helper functions.
"""


from ghidra.program.model.symbol import SourceType



class GhidraUtils(object):


    @staticmethod
    def address_string(address):

        if address is None:

            return None


        return str(address)



    @staticmethod
    def get_function_size(function):


        body = function.getBody()


        min_addr = body.getMinAddress()

        max_addr = body.getMaxAddress()


        return (

            max_addr.getOffset()

            -

            min_addr.getOffset()

            +

            1

        )



    @staticmethod
    def get_function_range(function):


        body = function.getBody()


        return {

            "start":
                str(
                    body.getMinAddress()
                ),

            "end":
                str(
                    body.getMaxAddress()
                )

        }



    @staticmethod
    def is_external(function):


        return function.isExternal()



    @staticmethod
    def get_namespace(function):


        namespace = function.getParentNamespace()


        if namespace:

            return namespace.getName()


        return ""
