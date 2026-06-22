from typing import List, Optional

import chromadb
from chromadb.config import Settings


class ChromaVectorStore:
    def __init__(
        self,
        collection_name: str = "default_collection",
        persist_dir: Optional[str] = None,
    ):
        self.collection_name = collection_name
        self.persist_dir = persist_dir

        self.client = self._init_client()

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

    def _init_client(self):
        """
        Initialize ChromaDB client.

        - persist_dir != None: Persistent mode
        - persist_dir == None: In-memory mode
        """

        if self.persist_dir:
            return chromadb.PersistentClient(
                path=self.persist_dir
            )

        return chromadb.Client(
            Settings(
                anonymized_telemetry=False
            )
        )

    def add(
        self,
        chunks: List[str],
        embeddings: List[List[float]]
    ) -> bool:
        """
        Add chunks and embeddings into collection.
        """

        if len(chunks) != len(embeddings):
            raise ValueError(
                "chunks and embeddings must have the same length"
            )

        start_idx = self.collection.count()

        ids = [
            f"chunk_{start_idx + i}"
            for i in range(len(chunks))
        ]

        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings
        )

        return True

    def get_collection_stats(self):
        """
        Return collection statistics.
        """

        return {
            "collection_name": self.collection_name,
            "count": self.collection.count()
        }

    def delete_collection(self) -> bool:
        """
        Delete the entire collection.
        """

        self.client.delete_collection(
            name=self.collection_name
        )

        return True