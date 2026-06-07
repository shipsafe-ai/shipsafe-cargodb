"""SchemaHarmonizer — reads collection schema and flags drift risk.

Read-only: only calls collection_schema MCP tool.
"""
from __future__ import annotations

from agent.config import MONGODB_DB, MONGODB_COLLECTION
from agent.mcp_client import MongoMCPClient

_DRIFT_THRESHOLD = 0.5


class SchemaHarmonizer:
    def __init__(self) -> None:
        self.db_name = MONGODB_DB
        self.collection_name = MONGODB_COLLECTION
        self.mcp_client = MongoMCPClient(
            db_name=self.db_name, collection_name=self.collection_name
        )

    async def analyze(self) -> dict:
        raw = await self.mcp_client.collection_schema()
        fields = raw.get("fields", [])
        annotated = []
        for f in fields:
            coverage = f.get("coverage", 1.0)
            annotated.append({**f, "drift_risk": coverage < _DRIFT_THRESHOLD})
        return {
            "collection": self.collection_name,
            "fields": annotated,
            "total_fields": len(annotated),
            "drift_fields": sum(1 for f in annotated if f["drift_risk"]),
        }
