"""RED tests for SchemaHarmonizer."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def harmonizer():
    from agent.specialists.schema_harmonizer import SchemaHarmonizer
    return SchemaHarmonizer()


class TestSchemaHarmonizerInit:
    def test_has_mcp_client(self, harmonizer):
        assert hasattr(harmonizer, "mcp_client")


class TestSchemaHarmonizerAnalyze:
    @pytest.mark.asyncio
    async def test_returns_schema_report(self, harmonizer):
        mock_schema = {
            "fields": [
                {"name": "decision_id", "type": "string", "coverage": 1.0},
                {"name": "decision_text", "type": "string", "coverage": 0.95},
                {"name": "embedding", "type": "array", "coverage": 0.80},
            ]
        }
        with patch.object(harmonizer, "mcp_client") as mock_mcp:
            mock_mcp.collection_schema = AsyncMock(return_value=mock_schema)
            report = await harmonizer.analyze()
            assert "fields" in report
            assert report["collection"] == "decisions"

    @pytest.mark.asyncio
    async def test_flags_low_coverage_fields(self, harmonizer):
        mock_schema = {
            "fields": [
                {"name": "decision_id", "type": "string", "coverage": 1.0},
                {"name": "optional_notes", "type": "string", "coverage": 0.3},
            ]
        }
        with patch.object(harmonizer, "mcp_client") as mock_mcp:
            mock_mcp.collection_schema = AsyncMock(return_value=mock_schema)
            report = await harmonizer.analyze()
            drift_fields = [f for f in report["fields"] if f.get("drift_risk")]
            assert any(f["name"] == "optional_notes" for f in drift_fields)

    @pytest.mark.asyncio
    async def test_harmonizer_is_read_only(self, harmonizer):
        """SchemaHarmonizer only reads — never writes/drops fields."""
        import inspect
        import agent.specialists.schema_harmonizer as mod
        src = inspect.getsource(mod)
        assert "insert" not in src.lower()
        assert "drop" not in src.lower()
        assert "delete" not in src.lower()
