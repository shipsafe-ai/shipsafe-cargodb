"""MemoryWriter — stores agent decisions via MongoDB MCP insert-many.

Vectorisation is handled entirely by the MCP server (server-side config).
No vector/similarity code in this module — compliance rule 1.
"""
from __future__ import annotations
from typing import Any

from agent.config import MONGODB_DB, MONGODB_COLLECTION
from agent.mcp_client import MongoMCPClient

_REQUIRED_FIELDS = ("decision_id", "decision_type", "decision_text")


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
        result = await self.mcp_client.insert_many(documents=[decision])
        return {"inserted_count": len(result.get("inserted_ids", []))}

    async def write_batch(self, decisions: list[dict]) -> dict:
        for d in decisions:
            self._validate(d)
        result = await self.mcp_client.insert_many(documents=decisions)
        return {"inserted_count": len(result.get("inserted_ids", []))}
