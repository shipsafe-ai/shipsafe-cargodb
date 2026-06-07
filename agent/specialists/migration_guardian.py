"""MigrationGuardian — assesses query/index safety via MCP explain.

Read-only: only calls explain, never mutates data.
"""
from __future__ import annotations

from agent.config import MONGODB_DB, MONGODB_COLLECTION
from agent.mcp_client import MongoMCPClient

_HIGH_DOCS_THRESHOLD = 1000


class MigrationGuardian:
    def __init__(self) -> None:
        self.db_name = MONGODB_DB
        self.collection_name = MONGODB_COLLECTION
        self.mcp_client = MongoMCPClient(
            db_name=self.db_name, collection_name=self.collection_name
        )

    async def assess_index_impact(self, proposed_query: dict) -> dict:
        plan = await self.mcp_client.explain(query=proposed_query)
        planner = plan.get("queryPlanner", {})
        stats = plan.get("executionStats", {})
        winning = planner.get("winningPlan", {})
        stage = winning.get("stage", "UNKNOWN")
        index_name = winning.get("indexName", None)
        docs_examined = stats.get("totalDocsExamined", 0)

        if stage == "COLLSCAN" or docs_examined > _HIGH_DOCS_THRESHOLD:
            risk = "HIGH"
            recommendation = (
                "Full collection scan detected. Add an index on the queried field(s) "
                "before running this query in production."
            )
        elif docs_examined > 100:
            risk = "MEDIUM"
            recommendation = "Consider adding a compound index to reduce docs examined."
        else:
            risk = "LOW"
            recommendation = "Query uses an index efficiently."

        return {
            "stage": stage,
            "index_used": index_name,
            "docs_examined": docs_examined,
            "risk_level": risk,
            "recommendation": recommendation,
        }
