import lancedb
from pathlib import Path
from typing import Optional
import asyncio
import uuid

from app.config import get_settings


class LanceDBService:
    """LanceDB service for vector storage and search."""

    def __init__(self, db_path: Optional[Path] = None):
        settings = get_settings()
        self.db_path = db_path or settings.lancedb_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = settings.nim_embedding_dim

        self._db = None

    @property
    def db(self):
        """Lazy connection to LanceDB."""
        if self._db is None:
            self._db = lancedb.connect(str(self.db_path))
        return self._db

    def _get_table_name(self, user_id: str) -> str:
        """Get table name for a user."""
        # Sanitize user_id for table name
        safe_id = user_id.replace("-", "_").replace(".", "_")
        return f"user_{safe_id}"

    def _ensure_table(self, user_id: str):
        """Ensure user table exists."""
        table_name = self._get_table_name(user_id)

        if table_name not in self.db.table_names():
            # Create empty table with schema
            self.db.create_table(
                table_name,
                data=[{
                    "chunk_id": "init",
                    "document_id": "init",
                    "notebook_id": "init",
                    "chunk_index": 0,
                    "text": "init",
                    "vector": [0.0] * self.embedding_dim
                }],
                mode="overwrite"
            )
            # Delete the init row
            table = self.db.open_table(table_name)
            table.delete('chunk_id = "init"')

        return self.db.open_table(table_name)

    async def add_vector(
        self,
        user_id: str,
        document_id: str,
        notebook_id: str,
        chunk_index: int,
        text: str,
        embedding: list[float]
    ):
        """Add a vector to user's table."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._add_vector_sync,
            user_id, document_id, notebook_id, chunk_index, text, embedding
        )

    def _add_vector_sync(
        self,
        user_id: str,
        document_id: str,
        notebook_id: str,
        chunk_index: int,
        text: str,
        embedding: list[float]
    ):
        """Synchronous add vector."""
        table = self._ensure_table(user_id)
        chunk_id = f"{document_id}_{chunk_index}"

        table.add([{
            "chunk_id": chunk_id,
            "document_id": document_id,
            "notebook_id": notebook_id,
            "chunk_index": chunk_index,
            "text": text,
            "vector": embedding
        }])

    async def search(
        self,
        user_id: str,
        query_embedding: list[float],
        notebook_id: Optional[str] = None,
        top_k: int = 5
    ) -> list[dict]:
        """
        Search for similar vectors.

        Args:
            user_id: User ID
            query_embedding: Query vector
            notebook_id: Optional notebook filter
            top_k: Number of results

        Returns:
            List of results with text, score, and metadata
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._search_sync,
            user_id, query_embedding, notebook_id, top_k
        )

    def _search_sync(
        self,
        user_id: str,
        query_embedding: list[float],
        notebook_id: Optional[str],
        top_k: int
    ) -> list[dict]:
        """Synchronous search."""
        table_name = self._get_table_name(user_id)

        if table_name not in self.db.table_names():
            return []

        table = self.db.open_table(table_name)

        # Build search query
        search = table.search(query_embedding)

        if notebook_id:
            search = search.where(f'notebook_id = "{notebook_id}"')

        results = search.limit(top_k).to_list()

        return [
            {
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "notebook_id": r["notebook_id"],
                "chunk_index": r["chunk_index"],
                "text": r["text"],
                "score": float(r["_distance"])  # Lower is better
            }
            for r in results
        ]

    async def delete_document_vectors(self, user_id: str, document_id: str):
        """Delete all vectors for a document."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._delete_document_sync,
            user_id, document_id
        )

    def _delete_document_sync(self, user_id: str, document_id: str):
        """Synchronous delete document vectors."""
        table_name = self._get_table_name(user_id)

        if table_name not in self.db.table_names():
            return

        table = self.db.open_table(table_name)
        table.delete(f'document_id = "{document_id}"')

    async def delete_notebook_vectors(self, user_id: str, notebook_id: str):
        """Delete all vectors for a notebook."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._delete_notebook_sync,
            user_id, notebook_id
        )

    def _delete_notebook_sync(self, user_id: str, notebook_id: str):
        """Synchronous delete notebook vectors."""
        table_name = self._get_table_name(user_id)

        if table_name not in self.db.table_names():
            return

        table = self.db.open_table(table_name)
        table.delete(f'notebook_id = "{notebook_id}"')

    async def delete_user_table(self, user_id: str):
        """Delete entire user table."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._delete_user_sync,
            user_id
        )

    def _delete_user_sync(self, user_id: str):
        """Synchronous delete user table."""
        table_name = self._get_table_name(user_id)

        if table_name in self.db.table_names():
            self.db.drop_table(table_name)

    async def get_user_stats(self, user_id: str) -> dict:
        """Get vector count stats for user."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_stats_sync,
            user_id
        )

    def _get_stats_sync(self, user_id: str) -> dict:
        """Synchronous get stats."""
        table_name = self._get_table_name(user_id)

        if table_name not in self.db.table_names():
            return {"vector_count": 0}

        table = self.db.open_table(table_name)
        return {"vector_count": len(table)}
