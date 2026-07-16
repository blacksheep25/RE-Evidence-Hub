import json


class FunctionRanker:


    def __init__(self):

        self.indicators = {

            # networking
            "socket": 8,
            "connect": 8,
            "recv": 6,
            "send": 6,
            "ws2": 8,
            "http": 5,

            # crypto
            "encrypt": 8,
            "decrypt": 8,
            "crypt": 6,
            "aes": 8,
            "rsa": 8,
            "sha": 5,

            # process manipulation
            "virtualalloc": 10,
            "writeprocessmemory": 10,
            "createremotethread": 10,
            "loadlibrary": 7,
            "getprocaddress": 7,

            # files
            "createfile": 5,
            "writefile": 5,
            "readfile": 3,

            # registry
            "regopen": 5,
            "regset": 5,

        }



    def score(
        self,
        item,
        query
    ):

        score = 0


        document = item.get(
            "document",
            ""
        ).lower()


        query = query.lower()



        # Query word matches

        for word in query.split():

            if word in document:
                score += 5



        # Security / malware indicators

        for key,value in self.indicators.items():

            if key in document:

                score += value



        try:

            fn = json.loads(
                item["document"]
            )


            calls = len(
                fn.get(
                    "calls",
                    []
                )
            )


            callers = len(
                fn.get(
                    "called_by",
                    []
                )
            )


            # Important functions have many callers

            if callers > 20:
                score += 3

            if callers > 100:
                score += 5


            if calls > 30:
                score += 2


            # Larger functions often contain logic

            c = fn.get(
                "decompiler",
                {}
            )


            if isinstance(c, dict):

                size = len(
                    c.get(
                        "c_code",
                        ""
                    )
                )

                score += min(
                    size / 5000,
                    5
                )


        except Exception:

            pass



        return score
