import os
import json
import chromadb
from sentence_transformers import SentenceTransformer


EXPORT = r"%USERPROFILE%\ghidra_ai_exports\sample_program"


db = chromadb.PersistentClient(
    path="./chroma"
)


collection = db.get_or_create_collection(
    "ghidra"
)


model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


documents = []
ids = []


def add_file(path):

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        data = json.load(f)


    text = json.dumps(
        data,
        indent=2
    )


    documents.append(text)

    ids.append(
        os.path.basename(path)
    )


# functions

function_dir = os.path.join(
    EXPORT,
    "functions"
)


for file in os.listdir(function_dir):

    if file.endswith(".json"):

        add_file(
            os.path.join(
                function_dir,
                file
            )
        )


print(
    "Loaded",
    len(documents),
    "functions"
)


embeddings = model.encode(
    documents
).tolist()


collection.add(

    ids=ids,

    documents=documents,

    embeddings=embeddings

)


print("Index complete")
