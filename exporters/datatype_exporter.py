"""
datatype_exporter.py

Exports Ghidra data types.

Exports:

- Structures
- Unions
- Enums
- Typedefs

Output:

types/
    structs.json
    unions.json
    enums.json
    typedefs.json
"""


import os


from ghidra.program.model.data import Structure
from ghidra.program.model.data import Union
from ghidra.program.model.data import Enum
from ghidra.program.model.data import TypedefDataType


from util.jsonwriter import JSONWriter



class DataTypeExporter(object):


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


        self.manager = (
            program
            .getDataTypeManager()
        )


        self.type_directory = os.path.join(

            output,

            "types"

        )


        if not os.path.exists(
            self.type_directory
        ):

            os.makedirs(
                self.type_directory
            )



    # --------------------------------------------------------
    # Main export
    # --------------------------------------------------------

    def export(self):


        structs = []

        unions = []

        enums = []

        typedefs = []



        iterator = (
            self.manager
            .getAllDataTypes()
        )


        while iterator.hasNext():


            datatype = iterator.next()



            try:


                if isinstance(
                    datatype,
                    Structure
                ):

                    structs.append(

                        self.export_structure(
                            datatype
                        )

                    )


                elif isinstance(
                    datatype,
                    Union
                ):

                    unions.append(

                        self.export_union(
                            datatype
                        )

                    )


                elif isinstance(
                    datatype,
                    Enum
                ):

                    enums.append(

                        self.export_enum(
                            datatype
                        )

                    )


                elif isinstance(
                    datatype,
                    TypedefDataType
                ):

                    typedefs.append(

                        self.export_typedef(
                            datatype
                        )

                    )


            except Exception as e:


                print(
                    "Datatype export failed: "
                    + str(e)
                )



        JSONWriter.save(

            os.path.join(
                self.type_directory,
                "structs.json"
            ),

            structs

        )


        JSONWriter.save(

            os.path.join(
                self.type_directory,
                "unions.json"
            ),

            unions

        )


        JSONWriter.save(

            os.path.join(
                self.type_directory,
                "enums.json"
            ),

            enums

        )


        JSONWriter.save(

            os.path.join(
                self.type_directory,
                "typedefs.json"
            ),

            typedefs

        )


        print(
            "[+] Exported datatypes"
        )



    # --------------------------------------------------------
    # Structures
    # --------------------------------------------------------

    def export_structure(
            self,
            struct):


        result = {}


        result["name"] = (
            struct.getName()
        )


        result["category"] = (
            str(
                struct.getCategoryPath()
            )
        )


        result["size"] = (
            struct.getLength()
        )


        result["fields"] = []


        components = (
            struct.getComponents()
        )


        for component in components:


            result["fields"].append({

                "name":
                    component.getFieldName(),

                "offset":
                    component.getOffset(),

                "size":
                    component.getLength(),

                "datatype":
                    str(
                        component
                        .getDataType()
                    )

            })


        return result



    # --------------------------------------------------------
    # Unions
    # --------------------------------------------------------

    def export_union(
            self,
            union):


        result = {}


        result["name"] = (
            union.getName()
        )


        result["size"] = (
            union.getLength()
        )


        result["fields"] = []


        for component in union.getComponents():


            result["fields"].append({

                "name":
                    component
                    .getFieldName(),

                "size":
                    component
                    .getLength(),

                "datatype":
                    str(
                        component
                        .getDataType()
                    )

            })


        return result



    # --------------------------------------------------------
    # Enums
    # --------------------------------------------------------

    def export_enum(
            self,
            enum):


        result = {}


        result["name"] = (
            enum.getName()
        )


        result["size"] = (
            enum.getLength()
        )


        result["values"] = []


        names = (
            enum.getNames()
        )


        for name in names:


            result["values"].append({

                "name":
                    name,

                "value":
                    enum.getValue(
                        name
                    )

            })


        return result



    # --------------------------------------------------------
    # Typedefs
    # --------------------------------------------------------

    def export_typedef(
            self,
            typedef):


        return {


            "name":
                typedef.getName(),


            "base_type":
                str(
                    typedef
                    .getDataType()
                ),


            "size":
                typedef.getLength()

        }
