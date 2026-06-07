"""MemoryWriter — stores agent decisions via MongoDB MCP insert-many.

Vectorisation: embeds decision_text via Voyage AI REST API before insert
(M0 Atlas does not support server-side auto-vectorization).
"""
from __future__ import annotations
import json
import os
import urllib.request
from typing import Any

from agent.config import MONGODB_DB, MONGODB_COLLECTION, VOYAGE_MODEL
from agent.mcp_client import MongoMCPClient
from agent.secrets import get_secret

_REQUIRED_FIELDS = ("decision_id", "decision_type", "decision_text")


def _embed_texts(texts: list[str]) -> list[list[float]]:
    api_key = os.environ.get("VOYAGE_API_KEY") or get_secret("VOYAGE_API_KEY")
    payload = json.dumps({"model": VOYAGE_MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        "https://api.voyageai.com/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return [item["embedding"] for item in data["data"]]


class MemoryWriter:
    def __init__(self) -> None:
        self.db_name = MONGODB_DB
        self.collection_name = MONGODB_COLLECTION
        self.mcp_client = MongoMCPClient(
            db_name=self.db_name, collection_name=self.collection_name
        )

    def _validate(self, decision: dict) -> None:
        for field in _REQUIRED_FIELDS:
            if field not in decision or not decision[field]:
                raise ValueError(f"Missing required field: {field}")

    async def write(self, decision: dict) -> dict:
        self._validate(decision)
        doc = dict(decision)
        if "embedding" not in doc:
            doc["embedding"] = _embed_texts([doc["decision_text"]])[0]
        result = await self.mcp_client.insert_many(documents=[doc])
        return {"inserted_count": len(result.get("inserted_ids", []))}

    async def write_batch(self, decisions: list[dict]) -> dict:
        for d in decisions:
            self._validate(d)
        docs = [dict(d) for d in decisions]
        to_embed = [i for i, d in enumerate(docs) if "embedding" not in d]
        if to_embed:
            texts = [docs[i]["decision_text"] for i in to_embed]
            embeddings = _embed_texts(texts)
            for i, emb in zip(to_embed, embeddings):
                docs[i]["embedding"] = emb
        result = await self.mcp_client.insert_many(documents=docs)
        return {"inserted_count": len(result.get("inserted_ids", []))}
