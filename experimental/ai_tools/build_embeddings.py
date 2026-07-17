import os
import json

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    USE_FUNCTION_RANKER,
    RANK_LIMIT
)

from function_ranker import FunctionRanker

EXPORT_PATH = "/data/sample_program.exe"

CHROMA_PATH = "/data/chroma"

COLLECTION_NAME = "ghidra"


# --------------------------------------------------
# Settings
# --------------------------------------------------

MAX_C_CODE = 6000
MAX_ASSEMBLY = 3000


print("[+] Loading embedding model...")

model = SentenceTransformer(
    "BAAI/bge-base-en-v1.5"
)


print("[+] Opening Chroma database...")

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)


try:
    client.delete_collection(
        COLLECTION_NAME
    )
except Exception:
    pass


collection = client.create_collection(
    COLLECTION_NAME
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def load_json(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return None



def get_names(items):

    result = []

    if not isinstance(items, list):
        return result


    for x in items:

        if isinstance(x, dict):

            name = x.get(
                "name",
                ""
            )

            if name:
                result.append(name)

        else:

            result.append(
                str(x)
            )

    return result



def get_string_values(items):

    result = []

    if not isinstance(items, list):
        return result


    for x in items:

        if isinstance(x, dict):

            value = (
                x.get("value")
                or
                x.get("string")
                or
                ""
            )

            if value:
                result.append(value)


        else:

            result.append(
                str(x)
            )

    return result



# --------------------------------------------------
# Load index
# --------------------------------------------------

index_file = os.path.join(
    EXPORT_PATH,
    "index.json"
)


index = load_json(
    index_file
)


if not index:

    raise Exception(
        "Missing index.json"
    )


functions = index["functions"]


# --------------------------------
# Optional function ranking
# --------------------------------

if USE_FUNCTION_RANKER:

    print(
        "[+] Function ranking enabled"
    )

    ranker = FunctionRanker(
        EXPORT_PATH
    )


    ranked = ranker.rank(
        RANK_LIMIT
    )


    selected = set(
        x["address"]
        for x in ranked
    )


    functions = {

        name:entry

        for name,entry in functions.items()

        if entry.get("address") in selected

    }


    print(
        f"[+] Selected {len(functions)} ranked functions"
    )


else:

    print(
        f"[+] Embedding all {len(functions)} functions"
    )


print(
    f"[+] Functions found: {len(functions)}"
)



# --------------------------------------------------
# Build embeddings
# --------------------------------------------------

count = 0

batch_ids = []
batch_docs = []
batch_embeddings = []
batch_metadata = []


BATCH_SIZE = 100



for name, entry in functions.items():


    filename = os.path.join(
        EXPORT_PATH,
        entry["file"]
    )


    fn = load_json(
        filename
    )


    if not fn:
        continue



    # --------------------------
    # Decompiled C
    # --------------------------

    decomp = fn.get(
        "decompiler",
        {}
    )


    if isinstance(decomp, dict):

        c_code = decomp.get(
            "c_code",
            ""
        )

    else:

        c_code = ""



    # --------------------------
    # Calls
    # --------------------------

    calls = get_names(
        fn.get(
            "calls",
            []
        )
    )



    # --------------------------
    # Called By
    # --------------------------

    called_by = get_names(
        fn.get(
            "called_by",
            []
        )
    )



    # --------------------------
    # Imports
    # --------------------------

    imports = get_names(
        fn.get(
            "imports",
            []
        )
    )



    # --------------------------
    # Strings
    # --------------------------

    strings = get_string_values(
        fn.get(
            "strings",
            []
        )
    )



    # --------------------------
    # Types
    # --------------------------

    types = get_names(
        fn.get(
            "types",
            []
        )
    )



    # --------------------------
    # Summary
    # --------------------------

    summary = (
        fn.get(
            "summary",
            ""
        )
        or
        fn.get(
            "ai_summary",
            ""
        )
    )



    # --------------------------
    # Globals
    # --------------------------

    globals_used = get_names(
        fn.get(
            "globals",
            []
        )
    )



    # --------------------------
    # Build document
    # --------------------------

    text = "\n".join([


        "FUNCTION:",
        fn.get(
            "name",
            ""
        ),


        "ADDRESS:",
        fn.get(
            "address",
            ""
        ),


        "SIGNATURE:",
        fn.get(
            "signature",
            ""
        ),


        "SUMMARY:",
        summary,


        "CALLS:",
        " ".join(calls),


        "CALLED BY:",
        " ".join(called_by),


        "IMPORTS:",
        " ".join(imports),


        "STRINGS:",
        " ".join(strings),


        "TYPES:",
        " ".join(types),


        "GLOBALS:",
        " ".join(globals_used),


        "C CODE:",
        c_code[:MAX_C_CODE],


        "ASSEMBLY:",
        fn.get(
            "assembly",
            ""
        )[:MAX_ASSEMBLY]

    ])



    # --------------------------
    # Embed
    # --------------------------

    embedding = model.encode(
        text,
        normalize_embeddings=True
    ).tolist()



    batch_ids.append(
        fn.get(
            "address",
            name
        )
    )

    batch_docs.append(
        text
    )

    batch_embeddings.append(
        embedding
    )

    batch_metadata.append({

        "name":
            fn.get(
                "name",
                ""
            ),

        "file":
            entry.get(
                "file",
                ""
            )

    })


    count += 1



    # --------------------------
    # Batch insert
    # --------------------------

    if len(batch_ids) >= BATCH_SIZE:


        collection.add(

            ids=batch_ids,

            embeddings=batch_embeddings,

            documents=batch_docs,

            metadatas=batch_metadata

        )


        batch_ids.clear()
        batch_docs.clear()
        batch_embeddings.clear()
        batch_metadata.clear()



    if count % 1000 == 0:

        print(
            f"{count} indexed"
        )



# --------------------------------------------------
# Final batch
# --------------------------------------------------

if batch_ids:

    collection.add(

        ids=batch_ids,

        embeddings=batch_embeddings,

        documents=batch_docs,

        metadatas=batch_metadata

    )


print(
    f"Done ({count})"
)
