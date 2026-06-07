"""PerformanceAdvisor — surfaces Atlas slow query + index suggestions via MCP.

Uses atlas-get-performance-advisor tool. Requires Atlas API credentials.
"""
from __future__ import annotations
import os

from agent.config import MONGODB_DB, MONGODB_COLLECTION
from agent.mcp_client import MongoMCPClient

_ATLAS_PROJECT_ID = os.environ.get("ATLAS_PROJECT_ID", "")
_ATLAS_CLUSTER_NAME = os.environ.get("ATLAS_CLUSTER_NAME", "shipsafe-cluster")


class PerformanceAdvisor:
    def __init__(self) -> None:
        self.db_name = MONGODB_DB
        self.collection_name = MONGODB_COLLECTION
        self.mcp_client = MongoMCPClient(
            db_name=self.db_name, collection_name=self.collection_name
        )

    async def get_recommendations(
        self,
        project_id: str = _ATLAS_PROJECT_ID,
        cluster_name: str = _ATLAS_CLUSTER_NAME,
    ) -> dict:
        """Fetch suggested indexes, slow queries, schema suggestions."""
        raw = await self.mcp_client.atlas_performance_advisor(
            project_id=project_id, cluster_name=cluster_name
        )
        suggested_indexes = raw.get("suggestedIndexes", [])
        slow_queries = raw.get("slowQueries", [])
        return {
            "suggested_indexes": suggested_indexes,
            "suggested_index_count": len(suggested_indexes),
            "slow_queries": slow_queries[:10],
            "slow_query_count": len(slow_queries),
            "has_recommendations": len(suggested_indexes) > 0,
        }

    async def get_collection_stats(self) -> dict:
        """Count + storage size + db stats via MCP."""
        doc_count = await self.mcp_client.count()
        storage = await self.mcp_client.collection_storage_size()
        db_stats = await self.mcp_client.db_stats()
        return {
            "collection": self.collection_name,
            "document_count": doc_count,
            "storage_size_bytes": storage.get("size", 0),
            "avg_doc_size_bytes": storage.get("avgObjSize", 0),
            "db_data_size_bytes": db_stats.get("dataSize", 0),
            "db_index_size_bytes": db_stats.get("indexSize", 0),
        }

    async def get_cluster_alerts(
        self,
        project_id: str = _ATLAS_PROJECT_ID,
    ) -> list[dict]:
        """Fetch active Atlas cluster alerts."""
        if not project_id:
            return []
        alerts = await self.mcp_client.atlas_list_alerts(project_id=project_id)
        return [
            {
                "id": a.get("id"),
                "type": a.get("eventTypeName"),
                "status": a.get("status"),
                "created": a.get("created"),
                "metric": a.get("metricName"),
            }
            for a in alerts
        ]
