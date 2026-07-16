import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_PATH = r"%USERPROFILE%\ghidra_ai_chroma"

print("[+] Loading model")

model = SentenceTransformer(
    "BAAI/bge-base-en-v1.5",
    device="cuda"
)


client = chromadb.PersistentClient(
    path=CHROMA_PATH
)


collection = client.get_collection(
    "ghidra"
)


print(collection)
print("Count:", collection.count())


query = "network packet encryption"


embedding = model.encode(
    query,
    normalize_embeddings=True
).tolist()


result = collection.query(
    query_embeddings=[
        embedding
    ],
    n_results=5
)


for i, doc in enumerate(result["documents"][0]):

    print("\n================")
    print("RESULT", i)

    print(
        result["metadatas"][0][i]
    )

    print(
        doc[:1000]
    )
