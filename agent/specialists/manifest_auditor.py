"""ManifestAuditor — queries cargo manifests from Atlas via MCP find + aggregate.

User-supplied cargo manifest fields are treated as structured data,
not passed freeform to any LLM (prompt-injection defense, rule 9).
"""
from __future__ import annotations
from typing import Optional

from agent.config import MONGODB_DB
from agent.mcp_client import MongoMCPClient

_MANIFESTS_COLLECTION = "cargo_manifests"


class ManifestAuditor:
    def __init__(self) -> None:
        self.db_name = MONGODB_DB
        self.collection_name = _MANIFESTS_COLLECTION
        self.mcp_client = MongoMCPClient(
            db_name=self.db_name, collection_name=self.collection_name
        )

    async def audit(self, vessel_id: Optional[str] = None) -> dict:
        query: dict = {}
        if vessel_id:
            query["vessel_id"] = vessel_id
        manifests = await self.mcp_client.find(filter=query, limit=200)
        return {
            "manifests": [
                {k: v for k, v in m.items() if k in (
                    "_id", "vessel_id", "cargo_type", "weight_tons",
                    "origin_port", "destination_port", "status"
                )}
                for m in manifests
            ],
            "count": len(manifests),
        }

    async def status_summary(self) -> dict:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        rows = await self.mcp_client.aggregate(pipeline=pipeline)
        return {"by_status": {r["_id"]: r["count"] for r in rows}}
