"""Tests for PerformanceAdvisor."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def advisor():
    from agent.specialists.performance_advisor import PerformanceAdvisor
    return PerformanceAdvisor()


class TestPerformanceAdvisorInit:
    def test_has_mcp_client(self, advisor):
        assert hasattr(advisor, "mcp_client")


class TestCollectionStats:
    @pytest.mark.asyncio
    async def test_returns_stats(self, advisor):
        with patch.object(advisor, "mcp_client") as mock_mcp:
            mock_mcp.count = AsyncMock(return_value=42)
            mock_mcp.collection_storage_size = AsyncMock(
                return_value={"size": 102400, "avgObjSize": 512}
            )
            mock_mcp.db_stats = AsyncMock(
                return_value={"dataSize": 204800, "indexSize": 8192}
            )
            stats = await advisor.get_collection_stats()
            assert stats["document_count"] == 42
            assert stats["storage_size_bytes"] == 102400
            assert stats["db_data_size_bytes"] == 204800

    @pytest.mark.asyncio
    async def test_stats_uses_three_mcp_tools(self, advisor):
        with patch.object(advisor, "mcp_client") as mock_mcp:
            mock_mcp.count = AsyncMock(return_value=0)
            mock_mcp.collection_storage_size = AsyncMock(return_value={})
            mock_mcp.db_stats = AsyncMock(return_value={})
            await advisor.get_collection_stats()
            mock_mcp.count.assert_called_once()
            mock_mcp.collection_storage_size.assert_called_once()
            mock_mcp.db_stats.assert_called_once()


class TestPerformanceRecommendations:
    @pytest.mark.asyncio
    async def test_returns_recommendations(self, advisor):
        mock_resp = {
            "suggestedIndexes": [
                {"index": {"decision_type": 1}, "impact": "HIGH"}
            ],
            "slowQueries": [
                {"op": "find", "ns": "cargodb_memory.decisions", "millis": 1200}
            ],
        }
        with patch.object(advisor, "mcp_client") as mock_mcp:
            mock_mcp.atlas_performance_advisor = AsyncMock(return_value=mock_resp)
            result = await advisor.get_recommendations(
                project_id="proj-123", cluster_name="shipsafe-cluster"
            )
            assert result["suggested_index_count"] == 1
            assert result["slow_query_count"] == 1
            assert result["has_recommendations"] is True

    @pytest.mark.asyncio
    async def test_no_recommendations_case(self, advisor):
        with patch.object(advisor, "mcp_client") as mock_mcp:
            mock_mcp.atlas_performance_advisor = AsyncMock(
                return_value={"suggestedIndexes": [], "slowQueries": []}
            )
            result = await advisor.get_recommendations(
                project_id="proj-123", cluster_name="shipsafe-cluster"
            )
            assert result["has_recommendations"] is False


class TestClusterAlerts:
    @pytest.mark.asyncio
    async def test_returns_alerts(self, advisor):
        mock_alerts = [
            {
                "id": "alert-001",
                "eventTypeName": "QUERY_TARGETING_SCANNED_OBJECTS_PER_RETURNED",
                "status": "OPEN",
                "created": "2024-06-01T00:00:00Z",
                "metricName": "QUERY_TARGETING_SCANNED_OBJECTS_PER_RETURNED",
            }
        ]
        with patch.object(advisor, "mcp_client") as mock_mcp:
            mock_mcp.atlas_list_alerts = AsyncMock(return_value=mock_alerts)
            alerts = await advisor.get_cluster_alerts(project_id="proj-123")
            assert len(alerts) == 1
            assert alerts[0]["type"] == "QUERY_TARGETING_SCANNED_OBJECTS_PER_RETURNED"

    @pytest.mark.asyncio
    async def test_empty_project_id_returns_empty(self, advisor):
        alerts = await advisor.get_cluster_alerts(project_id="")
        assert alerts == []
