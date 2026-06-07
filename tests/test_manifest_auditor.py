"""RED tests for ManifestAuditor."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def auditor():
    from agent.specialists.manifest_auditor import ManifestAuditor
    return ManifestAuditor()


@pytest.fixture
def sample_manifests():
    return [
        {
            "_id": "m-001",
            "vessel_id": "vessel-hormuz-01",
            "cargo_type": "crude_oil",
            "weight_tons": 250000,
            "origin_port": "Bandar Abbas",
            "destination_port": "Mumbai",
            "status": "in_transit",
        },
        {
            "_id": "m-002",
            "vessel_id": "vessel-hormuz-02",
            "cargo_type": "lng",
            "weight_tons": 80000,
            "origin_port": "Ras Laffan",
            "destination_port": "Singapore",
            "status": "delayed",
        },
    ]


class TestManifestAuditorInit:
    def test_has_mcp_client(self, auditor):
        assert hasattr(auditor, "mcp_client")


class TestManifestAuditorQuery:
    @pytest.mark.asyncio
    async def test_audit_returns_manifests(self, auditor, sample_manifests):
        with patch.object(auditor, "mcp_client") as mock_mcp:
            mock_mcp.find = AsyncMock(return_value=sample_manifests)
            result = await auditor.audit(vessel_id="vessel-hormuz-01")
            assert len(result["manifests"]) >= 1

    @pytest.mark.asyncio
    async def test_audit_aggregate_by_status(self, auditor):
        agg_result = [
            {"_id": "in_transit", "count": 5},
            {"_id": "delayed", "count": 2},
        ]
        with patch.object(auditor, "mcp_client") as mock_mcp:
            mock_mcp.aggregate = AsyncMock(return_value=agg_result)
            result = await auditor.status_summary()
            assert "by_status" in result
            assert result["by_status"]["in_transit"] == 5

    @pytest.mark.asyncio
    async def test_audit_filters_by_vessel(self, auditor, sample_manifests):
        filtered = [sample_manifests[0]]
        with patch.object(auditor, "mcp_client") as mock_mcp:
            mock_mcp.find = AsyncMock(return_value=filtered)
            result = await auditor.audit(vessel_id="vessel-hormuz-01")
            call_args = mock_mcp.find.call_args
            query = call_args[1].get("filter") or call_args[0][0]
            assert "vessel_id" in query

    @pytest.mark.asyncio
    async def test_manifest_fields_structured(self, auditor, sample_manifests):
        """Cargo manifest fields validated as structured — not free-form LLM input."""
        with patch.object(auditor, "mcp_client") as mock_mcp:
            mock_mcp.find = AsyncMock(return_value=sample_manifests)
            result = await auditor.audit()
            for m in result["manifests"]:
                assert "vessel_id" in m
                assert "cargo_type" in m
