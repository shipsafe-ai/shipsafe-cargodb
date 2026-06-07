"""RED tests for MigrationGuardian."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def guardian():
    from agent.specialists.migration_guardian import MigrationGuardian
    return MigrationGuardian()


class TestMigrationGuardianInit:
    def test_has_mcp_client(self, guardian):
        assert hasattr(guardian, "mcp_client")


class TestMigrationGuardianExplain:
    @pytest.mark.asyncio
    async def test_explain_returns_plan(self, guardian):
        mock_explain = {
            "queryPlanner": {
                "winningPlan": {"stage": "IXSCAN", "indexName": "decisions_vector_idx"}
            },
            "executionStats": {"totalDocsExamined": 100, "totalKeysExamined": 50},
        }
        with patch.object(guardian, "mcp_client") as mock_mcp:
            mock_mcp.explain = AsyncMock(return_value=mock_explain)
            result = await guardian.assess_index_impact(
                proposed_query={"decision_type": "routing"}
            )
            assert "index_used" in result
            assert "docs_examined" in result

    @pytest.mark.asyncio
    async def test_full_collection_scan_flagged(self, guardian):
        mock_explain = {
            "queryPlanner": {"winningPlan": {"stage": "COLLSCAN"}},
            "executionStats": {"totalDocsExamined": 10000, "totalKeysExamined": 0},
        }
        with patch.object(guardian, "mcp_client") as mock_mcp:
            mock_mcp.explain = AsyncMock(return_value=mock_explain)
            result = await guardian.assess_index_impact({"cargo_type": "crude_oil"})
            assert result["risk_level"] == "HIGH"
            assert result["recommendation"] != ""

    @pytest.mark.asyncio
    async def test_indexed_query_safe(self, guardian):
        mock_explain = {
            "queryPlanner": {
                "winningPlan": {
                    "stage": "IXSCAN",
                    "indexName": "decision_type_idx",
                }
            },
            "executionStats": {"totalDocsExamined": 20, "totalKeysExamined": 20},
        }
        with patch.object(guardian, "mcp_client") as mock_mcp:
            mock_mcp.explain = AsyncMock(return_value=mock_explain)
            result = await guardian.assess_index_impact({"decision_type": "routing"})
            assert result["risk_level"] in ("LOW", "MEDIUM")

    @pytest.mark.asyncio
    async def test_guardian_read_only(self, guardian):
        """MigrationGuardian only explains — never mutates data."""
        import inspect
        import agent.specialists.migration_guardian as mod
        src = inspect.getsource(mod)
        assert "insert" not in src.lower()
        assert "update" not in src.lower()
        assert "delete" not in src.lower()
