import os
import json

from config import FUNCTION_PATH, OUTPUT_PATH


def clean(text):

    if text is None:
        return ""

    return str(text)



def build_index():


    os.makedirs(
        OUTPUT_PATH,
        exist_ok=True
    )


    index = []


    files = os.listdir(
        FUNCTION_PATH
    )


    total = 0


    for filename in files:


        if not filename.endswith(".json"):
            continue


        path = os.path.join(
            FUNCTION_PATH,
            filename
        )


        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as f:

            function = json.load(f)



        entry = {

            "file":
                filename,


            "address":
                clean(
                    function.get("address")
                ),


            "name":
                clean(
                    function.get("name")
                ),


            "signature":
                clean(
                    function.get("signature")
                ),


            "calls":

                [
                    x.get("name","")
                    for x in function.get(
                        "calls",
                        []
                    )
                ],


            "text":

                "\n".join([

                    clean(function.get("name")),

                    clean(function.get("signature")),

                    clean(
                        function.get(
                            "decompiler",
                            {}
                        )
                        .get(
                            "c_code",
                            ""
                        )
                    ),

                    clean(
                        function.get(
                            "assembly",
                            ""
                        )
                    )

                ])

        }


        index.append(entry)

        total += 1


    output = os.path.join(
        OUTPUT_PATH,
        "index.json"
    )


    with open(
        output,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            index,
            f,
            indent=2
        )


    print(
        "[+] Indexed {} functions".format(
            total
        )
    )


    print(
        "[+] Saved:",
        output
    )



if __name__ == "__main__":

    build_index()
