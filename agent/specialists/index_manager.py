"""IndexManager — ensures decisions_vector_idx exists via MCP create-index.

Called at server startup. If index already exists, no-op.
Critical: without this, $vectorSearch silently returns nothing.
"""
from __future__ import annotations

from agent.config import (
    MONGODB_DB,
    MONGODB_COLLECTION,
    VECTOR_INDEX_NAME,
    VECTOR_DIMENSIONS,
    VOYAGE_MODEL,
)
from agent.mcp_client import MongoMCPClient

_VECTOR_INDEX_DEF = {
    "name": VECTOR_INDEX_NAME,
    "type": "vectorSearch",
    "definition": {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": VECTOR_DIMENSIONS,
                "similarity": "cosine",
            },
            {"type": "filter", "path": "decision_type"},
            {"type": "filter", "path": "timestamp"},
        ]
    },
}


class IndexManager:
    def __init__(self) -> None:
        self.db_name = MONGODB_DB
        self.collection_name = MONGODB_COLLECTION
        self.mcp_client = MongoMCPClient(
            db_name=self.db_name, collection_name=self.collection_name
        )

    async def ensure_vector_index(self) -> dict:
        """Create decisions_vector_idx if absent. Idempotent."""
        existing = await self.mcp_client.collection_indexes()
        names = [idx.get("name", "") for idx in existing]
        if VECTOR_INDEX_NAME in names:
            return {"status": "exists", "index": VECTOR_INDEX_NAME}

        result = await self.mcp_client.create_index(
            keys={"embedding": "vectorSearch"},
            options=_VECTOR_INDEX_DEF,
        )
        return {"status": "created", "index": VECTOR_INDEX_NAME, "result": result}

    async def index_status(self) -> dict:
        """Return all indexes + whether vector index exists."""
        existing = await self.mcp_client.collection_indexes()
        names = [idx.get("name", "") for idx in existing]
        return {
            "vector_index_present": VECTOR_INDEX_NAME in names,
            "vector_index_name": VECTOR_INDEX_NAME,
            "all_indexes": names,
            "total": len(existing),
        }
