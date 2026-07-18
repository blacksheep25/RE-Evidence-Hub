import json
import os
import re

NETWORK_WORDS = [
    "socket",
    "connect",
    "recv",
    "send",
    "packet",
    "network",
    "winsock",
    "ws2",
    "htons",
    "hton",
    "server",
    "client",
    "login",
    "gateway",
    "proxy",
    "session"
]


class HybridSearch:


    def __init__(self, export_path):

        # Keep the supported local evidence/HTTP/MCP surface importable without
        # the optional vector stack. This compatibility bridge is the only
        # supported-to-experimental link, so load it only when instantiated.
        from experimental.ai_tools.ranker import FunctionRanker
        from experimental.ai_tools.query import BinarySearch
        from experimental.ai_tools.embeddings import BinaryEmbeddings
        from experimental.ai_tools.memory import BinaryMemory
        from experimental.ai_tools.callgraph import CallGraph
        from experimental.ai_tools.ghidra_types import BinaryTypes
        from experimental.ai_tools.string_search import StringSearch
        from experimental.ai_tools.strings import BinaryStrings

        self.export_path = export_path


        self.search = BinarySearch(
            export_path
        )


        self.embeddings = BinaryEmbeddings()


        self.memory = BinaryMemory(
            export_path
        )


        self.ranker = FunctionRanker()


        self.string_hits = StringSearch(
            export_path
        )


        self.strings = BinaryStrings(
            export_path
        )


        self.callgraph = CallGraph(
            export_path
        )


        self.types = BinaryTypes(
            export_path
        )


        self.summaries = {}

        from experimental.ai_tools.function_namer import FunctionNamer

        self.namer = FunctionNamer(
            export_path
        )

        summary_file = os.path.join(
            export_path,
            "function_summaries.json"
        )


        if os.path.exists(summary_file):

            with open(
                summary_file,
                encoding="utf-8"
            ) as f:

                data=json.load(f)


            if isinstance(data,dict):

                self.summaries=data


            elif isinstance(data,list):

                for x in data:

                    if isinstance(x,dict):

                        n=x.get(
                            "name",
                            ""
                        )

                        if n:

                            self.summaries[n]=(
                                x.get("summary")
                                or
                                x.get("description")
                                or
                                ""
                            )


        print(
            "[+] Hybrid search ready"
        )



    def get_function(
            self,
            address):

        return self.search.find(
            address
        )



    def semantic(
            self,
            query,
            limit=10):


        result=self.embeddings.search(
            query,
            limit
        )


        output=[]


        if not result.get("ids"):
            return output


        for addr in result["ids"][0]:

            fn=self.get_function(
                addr
            )

            if fn:

                fn["ai_name"] = self.namer.analyze(
                    fn
                )

                output.append(
                    fn
                )


        return output



    def keyword(
            self,
            query,
            limit=10):


        results=self.search.search(
            query,
            limit
        )


        return [
            x["function"]
            for x in results
        ]



    def score_function(
            self,
            fn,
            query):


        text=json.dumps(
            fn
        ).lower()


        score=0


        name=fn.get(
            "name",
            ""
        ).lower()


        if "catch" in name:

            score-=50



        for word in NETWORK_WORDS:

            if word in query.lower():

                if word in text:

                    score+=20



        calls=json.dumps(
            fn.get(
                "calls",
                []
            )
        ).lower()



        for api in [
            "connect",
            "recv",
            "send",
            "socket",
            "wsagetlasterror",
            "htons"
        ]:

            if api in calls:

                score+=50



        score+=self.ranker.score(
            {
                "document":text,
                "metadata":{
                    "name":name
                }
            },
            query
        )


        return score




    def context(self, query):

        output = []

        output.append(
            "===== HYBRID BINARY ANALYSIS ====="
        )

        functions = []

        functions.extend(
            self.keyword(
                query,
                5
            )
        )

        functions.extend(
            self.semantic(
                query,
                10
            )
        )


        seen = set()
        unique = []

        for fn in functions:

            addr = fn.get(
                "address"
            )

            if addr and addr not in seen:

                seen.add(addr)

                unique.append(fn)



        ranked = []


        network_words = [
            "socket",
            "connect",
            "send",
            "recv",
            "recvfrom",
            "WSA",
            "htons",
            "hton",
            "inet",
            "select",
            "ioctl"
        ]


        for fn in unique:


            score = self.ranker.score(
                {
                    "document":
                        json.dumps(fn),

                    "metadata":
                    {
                        "name":
                            fn.get(
                                "name",
                                ""
                            )
                    }

                },
                query
            )


            text = json.dumps(
                fn
            ).lower()


            boost = 0


            for word in network_words:

                if word.lower() in text:

                    boost += 20



            ranked.append(
                (
                    score + boost,
                    fn
                )
            )


        ranked.sort(
            key=lambda x:x[0],
            reverse=True
        )


        top = [
            x[1]
            for x in ranked[:5]
        ]


        for fn in top:


            name = fn.get(
                "ai_name",
                fn.get(
                    "name",
                    "unknown"
                )
            )

            addr = fn.get(
                "address",
                ""
            )


            output.append(
                "\n===================="
            )


            output.append(
                f"{name} @ {addr}"
            )


            summary = self.summaries.get(
                name,
                ""
            )


            if summary:

                output.append(
                    "\nSummary:\n"
                    +
                    summary
                )



            calls = fn.get(
                "calls",
                []
            )


            if calls:

                output.append(
                    "\nImportant Calls:"
                )


                for c in calls[:15]:

                    if isinstance(c,dict):

                        output.append(
                            "- "
                            +
                            c.get(
                                "name",
                                ""
                            )
                        )



            decomp = fn.get(
                "decompiler",
                {}
            )


            code = ""


            if isinstance(
                decomp,
                dict
            ):

                code = decomp.get(
                    "c_code",
                    ""
                )


            if code:


                output.append(
                    "\nCode snippet:"
                )


                output.append(
                    code[:1200]
                )



        return "\n".join(
            output
        )
