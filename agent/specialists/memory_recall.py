"""MemoryRecall — retrieves similar decisions via Atlas $vectorSearch.

MCP handles query embedding server-side. Zero embedding code here.
"""
from __future__ import annotations
from typing import Optional

from agent.config import (
    MONGODB_DB,
    MONGODB_COLLECTION,
    VECTOR_INDEX_NAME,
    VECTOR_DIMENSIONS,
)
from agent.mcp_client import MongoMCPClient


class MemoryRecall:
    def __init__(self) -> None:
        self.db_name = MONGODB_DB
        self.collection_name = MONGODB_COLLECTION
        self.vector_index = VECTOR_INDEX_NAME
        self.mcp_client = MongoMCPClient(
            db_name=self.db_name, collection_name=self.collection_name
        )

    async def find_similar(
        self,
        query_text: str,
        decision_type: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        if not query_text or not query_text.strip():
            raise ValueError("query_text must not be empty")

        vs_stage: dict = {
            "$vectorSearch": {
                "index": self.vector_index,
                "queryVector": {"$vectorSearchQuery": query_text},
                "path": "embedding",
                "numCandidates": top_k * 10,
                "limit": top_k,
            }
        }
        if decision_type:
            vs_stage["$vectorSearch"]["filter"] = {"decision_type": {"$eq": decision_type}}

        pipeline = [
            vs_stage,
            {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            {"$project": {"embedding": 0}},
        ]

        return await self.mcp_client.aggregate(pipeline=pipeline)
