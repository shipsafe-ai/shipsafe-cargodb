"""MongoDB MCP client — real MCP calls to mongodb-mcp-server via stdio."""
from __future__ import annotations
import json
import os
import re
from contextlib import asynccontextmanager
from typing import Any, Optional

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from agent.secrets import get_secret


def _parse_mcp_content(text: str) -> Any:
    """Extract JSON from MCP tool response text.

    mongodb-mcp-server wraps document data in <untrusted-user-data-UUID> tags
    and emits three tag pairs per response (two in warning text, one wrapping data).
    The data pair is always the largest; find it by scanning all open/close positions
    and taking the span with the most content.
    """
    opens = [m.end() for m in re.finditer(r"<untrusted-user-data-[^>]+>", text)]
    closes = [m.start() for m in re.finditer(r"</untrusted-user-data-[^>]+>", text)]
    best_content = ""
    for o in opens:
        for c in closes:
            if c > o and len(text[o:c]) > len(best_content):
                best_content = text[o:c].strip()
                break
    if best_content:
        try:
            return json.loads(best_content)
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _try_secret(name: str) -> str:
    """Get secret value, return empty string on any error."""
    try:
        return get_secret(name)
    except Exception:
        return ""


def _encode_mongo_uri(uri: str) -> str:
    """URL-encode special chars in MongoDB URI credentials (RFC 3986)."""
    import re
    from urllib.parse import quote_plus
    match = re.match(r"(mongodb(?:\+srv)?://)([^:]+):(.+)@(.+)", uri)
    if not match:
        return uri
    scheme, user, pwd, rest = match.groups()
    return f"{scheme}{quote_plus(user)}:{quote_plus(pwd)}@{rest}"


def _build_server_params() -> StdioServerParameters:
    uri = os.environ.get("MONGODB_ATLAS_URI") or get_secret("MONGODB_ATLAS_URI")
    uri = _encode_mongo_uri(uri)
    voyage_key = os.environ.get("VOYAGE_API_KEY") or get_secret("VOYAGE_API_KEY")
    # Atlas API credentials — needed for performance advisor + alerts tools
    atlas_client_id = (
        os.environ.get("MDB_MCP_API_CLIENT_ID")
        or _try_secret("MDB_MCP_API_CLIENT_ID")
    )
    atlas_client_secret = (
        os.environ.get("MDB_MCP_API_CLIENT_SECRET")
        or _try_secret("MDB_MCP_API_CLIENT_SECRET")
    )
    env = {
        **os.environ,
        "MDB_MCP_CONNECTION_STRING": uri,
        "MDB_MCP_VOYAGE_API_KEY": voyage_key,
    }
    if atlas_client_id:
        env["MDB_MCP_API_CLIENT_ID"] = atlas_client_id
    if atlas_client_secret:
        env["MDB_MCP_API_CLIENT_SECRET"] = atlas_client_secret
    return StdioServerParameters(
        command="npx",
        args=["-y", "mongodb-mcp-server"],
        env=env,
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
        from anyio import BrokenResourceError
        _captured: list[Any] = []
        try:
            async with _mcp_session() as session:
                result = await session.call_tool(tool, arguments=arguments)
                # Use last content block — it contains the actual document data.
                # Earlier blocks are summary/metadata text.
                raw_text = result.content[-1].text if result.content else None
                if raw_text:
                    _captured.append(_parse_mcp_content(raw_text))
                else:
                    _captured.append(None)
        except* BrokenResourceError:
            # MCP subprocess exited after responding; cleanup task sees broken stream.
            # Tool call already completed — result captured above.
            pass
        return _captured[0] if _captured else None

    # ── Core CRUD ────────────────────────────────────────────────────────────

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

    # ── Schema & metadata ────────────────────────────────────────────────────

    async def collection_schema(self) -> dict:
        result = await self._call("collection-schema", {
            "database": self.db_name,
            "collection": self.collection_name,
        })
        return result if isinstance(result, dict) else {}

    async def collection_indexes(self) -> list[dict]:
        result = await self._call("collection-indexes", {
            "database": self.db_name,
            "collection": self.collection_name,
        })
        if isinstance(result, list):
            return result
        return result.get("indexes", []) if isinstance(result, dict) else []

    async def create_index(self, *, keys: dict, options: Optional[dict] = None) -> dict:
        args: dict = {
            "database": self.db_name,
            "collection": self.collection_name,
            "keys": keys,
        }
        if options:
            args["options"] = options
        result = await self._call("create-index", args)
        return result if isinstance(result, dict) else {"raw": result}

    async def count(self, *, filter: Optional[dict] = None) -> int:
        result = await self._call("count", {
            "database": self.db_name,
            "collection": self.collection_name,
            "query": filter or {},
        })
        if isinstance(result, int):
            return result
        if isinstance(result, dict):
            return result.get("count", 0)
        # Parse "Found N documents..." plain-text response
        if isinstance(result, str):
            m = re.search(r"\d+", result)
            return int(m.group()) if m else 0
        return 0

    async def collection_storage_size(self) -> dict:
        result = await self._call("collection-storage-size", {
            "database": self.db_name,
            "collection": self.collection_name,
        })
        return result if isinstance(result, dict) else {}

    async def db_stats(self) -> dict:
        result = await self._call("db-stats", {"database": self.db_name})
        return result if isinstance(result, dict) else {}

    # ── Query analysis ───────────────────────────────────────────────────────

    async def explain(self, *, query: dict) -> dict:
        result = await self._call("explain", {
            "database": self.db_name,
            "collection": self.collection_name,
            "filter": query,
        })
        return result if isinstance(result, dict) else {}

    # ── Atlas management (requires API credentials) ───────────────────────

    async def atlas_performance_advisor(self, *, project_id: str, cluster_name: str) -> dict:
        result = await self._call("atlas-get-performance-advisor", {
            "projectId": project_id,
            "clusterName": cluster_name,
        })
        return result if isinstance(result, dict) else {}

    async def atlas_list_alerts(self, *, project_id: str) -> list[dict]:
        result = await self._call("atlas-list-alerts", {"projectId": project_id})
        if isinstance(result, list):
            return result
        return result.get("alerts", []) if isinstance(result, dict) else []

    async def atlas_inspect_cluster(self, *, project_id: str, cluster_name: str) -> dict:
        result = await self._call("atlas-inspect-cluster", {
            "projectId": project_id,
            "clusterName": cluster_name,
        })
        return result if isinstance(result, dict) else {}

    async def search_knowledge(self, *, query: str, version: Optional[str] = None) -> list[dict]:
        args: dict = {"query": query}
        if version:
            args["version"] = version
        result = await self._call("search-knowledge", args)
        if isinstance(result, list):
            return result
        return result.get("results", []) if isinstance(result, dict) else []
