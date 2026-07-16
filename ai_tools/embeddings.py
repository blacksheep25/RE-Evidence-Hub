import chromadb
from sentence_transformers import SentenceTransformer

from host_config import (
    CHROMA_COLLECTION,
    DEFAULT_CHROMA_PATH,
    EMBEDDING_MODEL
)


class BinaryEmbeddings:

    def __init__(
        self,
        db_path=DEFAULT_CHROMA_PATH,
        model=EMBEDDING_MODEL
    ):

        self.model = SentenceTransformer(model)

        self.client = chromadb.PersistentClient(db_path)

        self.collection = self.client.get_or_create_collection(
            CHROMA_COLLECTION
        )

    def embed(self, text):

        return self.model.encode(
            text,
            normalize_embeddings=True
        ).tolist()

    def add(
        self,
        id,
        text,
        metadata
    ):

        self.collection.add(
            ids=[id],
            documents=[text],
            embeddings=[self.embed(text)],
            metadatas=[metadata]
        )

    def search(
        self,
        query,
        limit=10
    ):

        return self.collection.query(
            query_embeddings=[self.embed(query)],
            n_results=limit
        )
