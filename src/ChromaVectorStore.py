from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings


class ChromaVectorStore:
    """
    Chroma Vector Store

    Features:
    - In-memory mode
    - Persistent mode
    - Add chunks + embeddings
    - Similarity search
    - Collection statistics
    - Delete collection
    """

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
        Initialize Chroma client.

        Acceptance Criteria:
        - persist_dir != None -> persistent mode
        - persist_dir == None -> in-memory mode
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

        Returns
        -------
        bool
            True if successful
        """

        if len(chunks) != len(embeddings):
            raise ValueError(
                "chunks and embeddings must have same length"
            )

        ids = [
            f"chunk_{i}"
            for i in range(self.collection.count(),
                           self.collection.count() + len(chunks))
        ]

        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings
        )

        return True

    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search top-k similar chunks.
        """

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )

        documents = result.get("documents", [[]])[0]
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]

        output = []

        for doc_id, doc, dist in zip(
            ids,
            documents,
            distances
        ):
            output.append(
                {
                    "id": doc_id,
                    "document": doc,
                    "distance": dist
                }
            )

        return output

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Acceptance Criteria:
        Return collection statistics.
        """

        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "persist_dir": self.persist_dir,
            "mode": (
                "persistent"
                if self.persist_dir
                else "in-memory"
            ),
        }

    def delete_collection(self) -> bool:
        """
        Acceptance Criteria:
        Delete collection completely.
        """

        self.client.delete_collection(
            name=self.collection_name
        )

        return True

    def reset_collection(self) -> bool:
        """
        Optional helper method.
        """

        try:
            self.client.delete_collection(
                self.collection_name
            )
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

        return True