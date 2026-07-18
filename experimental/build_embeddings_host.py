import os
import json
import time

import chromadb
from sentence_transformers import SentenceTransformer

from host_config import (
    CHROMA_COLLECTION,
    DEFAULT_CHROMA_PATH,
    DEFAULT_EXPORT_PATH,
    EMBEDDING_MODEL
)


# ==================================================
# Settings
# ==================================================

EXPORT_PATH = DEFAULT_EXPORT_PATH

# Must match Docker mount:
# -v "%USERPROFILE%\ghidra_ai_chroma:/data/chroma"
CHROMA_PATH = DEFAULT_CHROMA_PATH

COLLECTION_NAME = CHROMA_COLLECTION


# Optional future ranking system
USE_RANKER = False


MAX_C_CODE = 6000
MAX_ASSEMBLY = 3000


# Embedding batch size
EMBED_BATCH_SIZE = 64

# Chroma insert batch
CHROMA_BATCH_SIZE = 500


# ==================================================
# Model
# ==================================================

print("[+] Loading embedding model...")


try:

    model = SentenceTransformer(
        EMBEDDING_MODEL,
        device="cuda"
    )

    print("[+] Using CUDA")

except Exception:

    print("[!] CUDA unavailable, using CPU")

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )



# ==================================================
# Chroma
# ==================================================

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



# ==================================================
# Helpers
# ==================================================

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


    for item in items:

        if isinstance(item, dict):

            name = item.get(
                "name",
                ""
            )

            if name:
                result.append(name)

        else:

            result.append(
                str(item)
            )


    return result



def get_strings(items):

    result = []

    if not isinstance(items, list):
        return result


    for item in items:

        if isinstance(item, dict):

            value = (
                item.get("value")
                or
                item.get("string")
                or
                ""
            )

            if value:
                result.append(value)

        else:

            result.append(
                str(item)
            )


    return result



def get_external_calls(items):

    result = []

    if not isinstance(items, list):
        return result


    for item in items:

        if isinstance(item, dict):

            if item.get("external"):

                name = item.get(
                    "name",
                    ""
                )

                if name:
                    result.append(name)


    return result



# ==================================================
# Load index
# ==================================================

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


functions = index.get(
    "functions",
    {}
)


print(
    f"[+] Functions found: {len(functions)}"
)



# ==================================================
# Embedding build
# ==================================================

start = time.time()

count = 0


batch_ids = []
batch_docs = []
batch_metadata = []



def flush_batch():

    global batch_ids
    global batch_docs
    global batch_metadata


    if not batch_ids:
        return


    embeddings = model.encode(
        batch_docs,
        batch_size=EMBED_BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=False
    )


    collection.add(

        ids=batch_ids,

        embeddings=embeddings.tolist(),

        documents=batch_docs,

        metadatas=batch_metadata

    )


    batch_ids = []
    batch_docs = []
    batch_metadata = []



# ==================================================
# Process functions
# ==================================================

for name, entry in functions.items():


    filename = os.path.join(
        EXPORT_PATH,
        entry.get(
            "file",
            ""
        )
    )


    fn = load_json(
        filename
    )


    if not fn:
        continue



    decomp = fn.get(
        "decompiler",
        {}
    )


    if isinstance(
        decomp,
        dict
    ):

        c_code = decomp.get(
            "c_code",
            ""
        )

    else:

        c_code = ""



    calls = get_names(
        fn.get(
            "calls",
            []
        )
    )


    called_by = get_names(
        fn.get(
            "called_by",
            []
        )
    )


    imports = get_names(
        fn.get(
            "imports",
            []
        )
    )


    external = get_external_calls(
        fn.get(
            "calls",
            []
        )
    )


    strings = get_strings(
        fn.get(
            "strings",
            []
        )
    )


    types = get_names(
        fn.get(
            "types",
            []
        )
    )


    globals_used = get_names(
        fn.get(
            "globals",
            []
        )
    )


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


        "EXTERNAL APIS:",
        " ".join(external),


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



    batch_ids.append(
        fn.get(
            "address",
            name
        )
    )


    batch_docs.append(
        text
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



    if len(batch_ids) >= CHROMA_BATCH_SIZE:

        flush_batch()



    if count % 1000 == 0:

        elapsed = time.time() - start

        rate = count / elapsed


        print(
            f"{count} indexed "
            f"({rate:.1f} funcs/sec)"
        )



# Final batch

flush_batch()



elapsed = time.time() - start


print()
print("==============================")
print(
    f"Done ({count})"
)
print(
    f"Time: {elapsed/60:.2f} minutes"
)
print(
    f"Speed: {count/elapsed:.1f} funcs/sec"
)
print("==============================")
