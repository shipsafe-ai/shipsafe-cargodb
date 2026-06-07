"""Thin async wrapper around MongoDB MCP server tools."""
from __future__ import annotations
import os
from typing import Any


class MongoMCPClient:
    """Delegates to mongodb-mcp-server MCP tools.

    In production, these methods are wired to MCP tool calls.
    In tests, patch this class directly.
    """

    def __init__(self, db_name: str, collection_name: str):
        self.db_name = db_name
        self.collection_name = collection_name

    async def insert_many(self, *, documents: list[dict]) -> dict:
        raise NotImplementedError("Wire to MCP insert-many tool")

    async def aggregate(self, *, pipeline: list[dict]) -> list[dict]:
        raise NotImplementedError("Wire to MCP aggregate tool")

    async def find(self, *, filter: dict, limit: int = 100) -> list[dict]:
        raise NotImplementedError("Wire to MCP find tool")

    async def collection_schema(self) -> dict:
        raise NotImplementedError("Wire to MCP collection-schema tool")

    async def explain(self, *, query: dict) -> dict:
        raise NotImplementedError("Wire to MCP explain tool")
