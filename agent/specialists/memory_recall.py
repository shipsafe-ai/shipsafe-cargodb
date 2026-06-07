"""MemoryRecall — retrieves similar decisions via Atlas $vectorSearch.

Query text is embedded via Voyage AI REST API (query-time only).
Insert-time embedding is handled separately (seed_atlas.py / MemoryWriter).
"""
from __future__ import annotations
import json
import os
import urllib.request
from typing import Optional

from agent.config import (
    MONGODB_DB,
    MONGODB_COLLECTION,
    VECTOR_INDEX_NAME,
    VOYAGE_MODEL,
)
from agent.mcp_client import MongoMCPClient
from agent.secrets import get_secret


def _embed_query(text: str) -> list[float]:
    """Embed a single query string via Voyage AI REST API."""
    api_key = os.environ.get("VOYAGE_API_KEY") or get_secret("VOYAGE_API_KEY")
    payload = json.dumps({"model": VOYAGE_MODEL, "input": [text]}).encode()
    req = urllib.request.Request(
        "https://api.voyageai.com/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data["data"][0]["embedding"]


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

        query_vector = _embed_query(query_text)

        vs_stage: dict = {
            "$vectorSearch": {
                "index": self.vector_index,
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": top_k * 10,
                "limit": top_k,
            }
        }
        if decision_type:
            vs_stage["$vectorSearch"]["filter"] = {
                "decision_type": {"$eq": decision_type}
            }

        pipeline = [
            vs_stage,
            {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            {"$project": {"embedding": 0}},
        ]

        return await self.mcp_client.aggregate(pipeline=pipeline)
