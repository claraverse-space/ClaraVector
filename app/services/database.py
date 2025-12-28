import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid

from app.config import get_settings


SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notebooks table
CREATE TABLE IF NOT EXISTS notebooks (
    notebook_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_notebooks_user ON notebooks(user_id);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    file_hash TEXT,
    chunk_count INTEGER DEFAULT 0,
    processing_status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(notebook_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_documents_notebook ON documents(notebook_id);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);

-- Embedding queue table (persistent)
CREATE TABLE IF NOT EXISTS embedding_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_queue_status ON embedding_queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_queue_document ON embedding_queue(document_id);
"""


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        settings = get_settings()
        self.db_path = db_path or settings.sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    # ==================== User Operations ====================

    async def create_user(self, user_id: str) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,)
            )
            await db.commit()
            return await self.get_user(user_id)

    async def get_user(self, user_id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_user(self, user_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    # ==================== Notebook Operations ====================

    async def create_notebook(
        self, user_id: str, name: str, description: Optional[str] = None
    ) -> dict:
        notebook_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO notebooks (notebook_id, user_id, name, description)
                   VALUES (?, ?, ?, ?)""",
                (notebook_id, user_id, name, description)
            )
            await db.commit()
        return await self.get_notebook(notebook_id)

    async def get_notebook(self, notebook_id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT n.*, COUNT(d.document_id) as document_count
                   FROM notebooks n
                   LEFT JOIN documents d ON n.notebook_id = d.notebook_id
                   WHERE n.notebook_id = ?
                   GROUP BY n.notebook_id""",
                (notebook_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_notebooks(self, user_id: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT n.*, COUNT(d.document_id) as document_count
                   FROM notebooks n
                   LEFT JOIN documents d ON n.notebook_id = d.notebook_id
                   WHERE n.user_id = ?
                   GROUP BY n.notebook_id
                   ORDER BY n.updated_at DESC""",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_notebook(
        self, notebook_id: str, name: Optional[str] = None, description: Optional[str] = None
    ) -> Optional[dict]:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if not updates:
            return await self.get_notebook(notebook_id)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(notebook_id)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE notebooks SET {', '.join(updates)} WHERE notebook_id = ?",
                params
            )
            await db.commit()
        return await self.get_notebook(notebook_id)

    async def delete_notebook(self, notebook_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM notebooks WHERE notebook_id = ?",
                (notebook_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_notebook_user_id(self, notebook_id: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT user_id FROM notebooks WHERE notebook_id = ?",
                (notebook_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    # ==================== Document Operations ====================

    async def create_document(
        self,
        notebook_id: str,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        file_hash: Optional[str] = None
    ) -> dict:
        document_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO documents
                   (document_id, notebook_id, user_id, filename, file_type, file_size, file_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (document_id, notebook_id, user_id, filename, file_type, file_size, file_hash)
            )
            await db.commit()
        return await self.get_document(document_id)

    async def get_document(self, document_id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM documents WHERE document_id = ?",
                (document_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_notebook_documents(self, notebook_id: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM documents
                   WHERE notebook_id = ?
                   ORDER BY created_at DESC""",
                (notebook_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_user_documents(self, user_id: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM documents
                   WHERE user_id = ?
                   ORDER BY created_at DESC""",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_document_status(
        self,
        document_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        async with aiosqlite.connect(self.db_path) as db:
            if chunk_count is not None:
                await db.execute(
                    """UPDATE documents
                       SET processing_status = ?, chunk_count = ?, error_message = ?,
                           processed_at = CASE WHEN ? IN ('completed', 'failed')
                                          THEN CURRENT_TIMESTAMP ELSE processed_at END
                       WHERE document_id = ?""",
                    (status, chunk_count, error_message, status, document_id)
                )
            else:
                await db.execute(
                    """UPDATE documents
                       SET processing_status = ?, error_message = ?,
                           processed_at = CASE WHEN ? IN ('completed', 'failed')
                                          THEN CURRENT_TIMESTAMP ELSE processed_at END
                       WHERE document_id = ?""",
                    (status, error_message, status, document_id)
                )
            await db.commit()

    async def delete_document(self, document_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_document_user_id(self, document_id: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT user_id FROM documents WHERE document_id = ?",
                (document_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    # ==================== Queue Operations ====================

    async def enqueue_chunks(self, document_id: str, chunks: list[dict]):
        async with aiosqlite.connect(self.db_path) as db:
            for i, chunk in enumerate(chunks):
                await db.execute(
                    """INSERT INTO embedding_queue (document_id, chunk_index, chunk_text)
                       VALUES (?, ?, ?)""",
                    (document_id, i, chunk["text"])
                )
            await db.commit()

    async def get_next_pending_chunk(self) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM embedding_queue
                   WHERE status = 'pending'
                   ORDER BY created_at ASC
                   LIMIT 1"""
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    row_dict = dict(row)
                    await db.execute(
                        "UPDATE embedding_queue SET status = 'processing' WHERE queue_id = ?",
                        (row_dict["queue_id"],)
                    )
                    await db.commit()
                    return row_dict
                return None

    async def mark_chunk_completed(self, queue_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE embedding_queue
                   SET status = 'completed', processed_at = CURRENT_TIMESTAMP
                   WHERE queue_id = ?""",
                (queue_id,)
            )
            await db.commit()

    async def mark_chunk_failed(self, queue_id: int, error: str, max_retries: int = 3):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT retry_count FROM embedding_queue WHERE queue_id = ?",
                (queue_id,)
            ) as cursor:
                row = await cursor.fetchone()
                retry_count = row[0] if row else 0

            if retry_count < max_retries:
                await db.execute(
                    """UPDATE embedding_queue
                       SET status = 'pending', retry_count = retry_count + 1, error_message = ?
                       WHERE queue_id = ?""",
                    (error, queue_id)
                )
            else:
                await db.execute(
                    """UPDATE embedding_queue
                       SET status = 'failed', error_message = ?, processed_at = CURRENT_TIMESTAMP
                       WHERE queue_id = ?""",
                    (error, queue_id)
                )
            await db.commit()

    async def get_queue_stats(self) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            for status in ["pending", "processing", "completed", "failed"]:
                async with db.execute(
                    "SELECT COUNT(*) FROM embedding_queue WHERE status = ?",
                    (status,)
                ) as cursor:
                    row = await cursor.fetchone()
                    stats[status] = row[0]
            return stats

    async def get_document_queue_status(self, document_id: str) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            stats = {"total": 0, "pending": 0, "processing": 0, "completed": 0, "failed": 0}
            async with db.execute(
                """SELECT status, COUNT(*) as count
                   FROM embedding_queue
                   WHERE document_id = ?
                   GROUP BY status""",
                (document_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    stats[row[0]] = row[1]
                    stats["total"] += row[1]
            return stats

    async def check_document_completed(self, document_id: str) -> bool:
        """Check if all chunks for a document are processed."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT COUNT(*) FROM embedding_queue
                   WHERE document_id = ? AND status NOT IN ('completed', 'failed')""",
                (document_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] == 0
