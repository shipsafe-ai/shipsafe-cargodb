"""MongoDB MCP client — real MCP calls to mongodb-mcp-server via stdio."""
from __future__ import annotations
import json
import os
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from agent.secrets import get_secret


def _build_server_params() -> StdioServerParameters:
    uri = os.environ.get("MONGODB_ATLAS_URI") or get_secret("MONGODB_ATLAS_URI")
    voyage_key = os.environ.get("VOYAGE_API_KEY") or get_secret("VOYAGE_API_KEY")
    return StdioServerParameters(
        command="npx",
        args=["-y", "mongodb-mcp-server"],
        env={
            **os.environ,
            "MDB_CONNECTION_STRING": uri,
            "VOYAGE_API_KEY": voyage_key,
        },
    )


@asynccontextmanager
async def _mcp_session():
    params = _build_server_params()
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            yield session


class MongoMCPClient:
    """Calls mongodb-mcp-server tools via MCP stdio transport."""

    def __init__(self, db_name: str, collection_name: str):
        self.db_name = db_name
        self.collection_name = collection_name

    async def _call(self, tool: str, arguments: dict) -> Any:
        async with _mcp_session() as session:
            result = await session.call_tool(tool, arguments=arguments)
            if result.content:
                raw = result.content[0].text
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, AttributeError):
                    return raw
            return None

    async def insert_many(self, *, documents: list[dict]) -> dict:
        result = await self._call("insert-many", {
            "database": self.db_name,
            "collection": self.collection_name,
            "documents": documents,
        })
        ids = result.get("insertedIds", []) if isinstance(result, dict) else []
        return {"inserted_ids": list(ids.values()) if isinstance(ids, dict) else ids}

    async def aggregate(self, *, pipeline: list[dict]) -> list[dict]:
        result = await self._call("aggregate", {
            "database": self.db_name,
            "collection": self.collection_name,
            "pipeline": pipeline,
        })
        if isinstance(result, list):
            return result
        return result.get("documents", []) if isinstance(result, dict) else []

    async def find(self, *, filter: dict, limit: int = 100) -> list[dict]:
        result = await self._call("find", {
            "database": self.db_name,
            "collection": self.collection_name,
            "filter": filter,
            "limit": limit,
        })
        if isinstance(result, list):
            return result
        return result.get("documents", []) if isinstance(result, dict) else []

    async def collection_schema(self) -> dict:
        result = await self._call("collection-schema", {
            "database": self.db_name,
            "collection": self.collection_name,
        })
        return result if isinstance(result, dict) else {}

    async def explain(self, *, query: dict) -> dict:
        result = await self._call("explain", {
            "database": self.db_name,
            "collection": self.collection_name,
            "filter": query,
        })
        return result if isinstance(result, dict) else {}
