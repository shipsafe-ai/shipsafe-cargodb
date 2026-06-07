"""Tests for FastAPI server endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

import agent.server as server_module
from agent.server import app


@pytest.fixture(autouse=True)
def mock_server_deps():
    """Inject mock specialists into server module globals."""
    from agent.config import VECTOR_INDEX_NAME

    mock_orchestrator = MagicMock()
    mock_orchestrator.run = AsyncMock(return_value={
        "decision_id": "dec-test-001",
        "similar_decisions": [],
        "candidate_decision": {
            "decision_id": "dec-test-001",
            "decision_type": "routing",
            "decision_text": "Reroute via Cape",
            "recommended_action": "reroute_cape",
            "confidence": 0.85,
        },
        "verdict": {"approved": True, "concerns": [], "risk_level": "LOW", "requires_human_approval": True},
        "status": "pending_approval",
    })
    mock_orchestrator.memory_writer = MagicMock()
    mock_orchestrator.memory_writer.write = AsyncMock(return_value={"inserted_count": 1})

    mock_recall = MagicMock()
    mock_recall.find_similar = AsyncMock(return_value=[
        {
            "decision_id": "dec-001",
            "decision_text": "Reroute via Cape",
            "decision_type": "routing",
            "score": 0.89,
        }
    ])

    mock_harmonizer = MagicMock()
    mock_harmonizer.analyze = AsyncMock(return_value={
        "collection": "decisions",
        "fields": [{"name": "decision_id", "type": "string", "coverage": 1.0, "drift_risk": False}],
        "total_fields": 1,
        "drift_fields": 0,
    })

    mock_index_manager = MagicMock()
    mock_index_manager.index_status = AsyncMock(return_value={
        "vector_index_present": True,
        "vector_index_name": VECTOR_INDEX_NAME,
        "all_indexes": [VECTOR_INDEX_NAME, "_id_"],
        "total": 2,
    })
    mock_index_manager.ensure_vector_index = AsyncMock(return_value={"status": "exists", "index": VECTOR_INDEX_NAME})

    mock_perf = MagicMock()
    mock_perf.get_collection_stats = AsyncMock(return_value={
        "collection": "decisions",
        "document_count": 5,
        "storage_size_bytes": 1024,
        "avg_doc_size_bytes": 256,
        "db_data_size_bytes": 2048,
        "db_index_size_bytes": 512,
    })
    mock_perf.get_cluster_alerts = AsyncMock(return_value=[])

    server_module._orchestrator = mock_orchestrator
    server_module._recall = mock_recall
    server_module._harmonizer = mock_harmonizer
    server_module._index_manager = mock_index_manager
    server_module._perf_advisor = mock_perf
    server_module._pending = {}

    yield {
        "orchestrator": mock_orchestrator,
        "recall": mock_recall,
        "harmonizer": mock_harmonizer,
        "index_manager": mock_index_manager,
        "perf_advisor": mock_perf,
    }


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "cargodb"


class TestRunEndpoint:
    @pytest.mark.asyncio
    async def test_run_accepts_event(self, client):
        payload = {
            "event_id": "evt-001",
            "event_type": "strait_closure",
            "affected_strait": "Hormuz",
            "vessels_affected": ["v-001"],
            "severity": "CRITICAL",
        }
        resp = await client.post("/run", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "decision_id" in data
        assert data["status"] in ("pending_approval", "completed")

    @pytest.mark.asyncio
    async def test_run_adds_to_pending(self, client):
        payload = {
            "event_id": "evt-002",
            "event_type": "strait_closure",
            "affected_strait": "Hormuz",
            "vessels_affected": [],
            "severity": "HIGH",
        }
        resp = await client.post("/run", json=payload)
        assert resp.status_code == 200
        decision_id = resp.json()["decision_id"]
        assert decision_id in server_module._pending


class TestDecisionsEndpoint:
    @pytest.mark.asyncio
    async def test_decisions_returns_list(self, client):
        resp = await client.get("/decisions")
        assert resp.status_code == 200
        data = resp.json()
        assert "decisions" in data
        assert "count" in data

    @pytest.mark.asyncio
    async def test_similar_search(self, client):
        resp = await client.post("/decisions/similar", json={"query_text": "reroute hormuz", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "decisions" in data


class TestApproveEndpoint:
    @pytest.mark.asyncio
    async def test_approve_not_found(self, client):
        resp = await client.post("/approve", json={
            "decision_id": "nonexistent",
            "approved": True,
            "approver": "operator",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_pending_decision(self, client, mock_server_deps):
        server_module._pending["dec-pending-001"] = {
            "decision_id": "dec-pending-001",
            "candidate_decision": {
                "decision_id": "dec-pending-001",
                "decision_type": "routing",
                "decision_text": "Reroute",
                "recommended_action": "reroute_cape",
                "confidence": 0.9,
            },
        }
        resp = await client.post("/approve", json={
            "decision_id": "dec-pending-001",
            "approved": True,
            "approver": "captain",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["approver"] == "captain"
        assert "dec-pending-001" not in server_module._pending

    @pytest.mark.asyncio
    async def test_reject_pending_decision(self, client, mock_server_deps):
        server_module._pending["dec-pending-002"] = {
            "decision_id": "dec-pending-002",
            "candidate_decision": {"decision_id": "dec-pending-002", "decision_text": "x",
                                    "decision_type": "routing", "recommended_action": "x", "confidence": 0.5},
        }
        resp = await client.post("/approve", json={
            "decision_id": "dec-pending-002",
            "approved": False,
            "approver": "captain",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"


class TestSchemaEndpoint:
    @pytest.mark.asyncio
    async def test_schema_returns_report(self, client):
        resp = await client.get("/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "collection" in data
        assert "fields" in data


class TestPendingEndpoint:
    @pytest.mark.asyncio
    async def test_pending_empty(self, client):
        resp = await client.get("/decisions/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0


class TestIndexEndpoints:
    @pytest.mark.asyncio
    async def test_index_status(self, client):
        resp = await client.get("/indexes")
        assert resp.status_code == 200
        data = resp.json()
        assert "vector_index_present" in data
        assert data["vector_index_present"] is True

    @pytest.mark.asyncio
    async def test_ensure_indexes(self, client):
        resp = await client.post("/indexes/ensure")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("exists", "created")


class TestStatsEndpoint:
    @pytest.mark.asyncio
    async def test_stats_returns_counts(self, client):
        resp = await client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "document_count" in data
        assert "storage_size_bytes" in data


class TestAlertsEndpoint:
    @pytest.mark.asyncio
    async def test_alerts_empty(self, client):
        resp = await client.get("/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data


class TestPerformanceEndpoint:
    @pytest.mark.asyncio
    async def test_performance_with_project_id(self, client, mock_server_deps):
        mock_server_deps["perf_advisor"].get_recommendations = AsyncMock(return_value={
            "suggested_indexes": [],
            "suggested_index_count": 0,
            "slow_queries": [],
            "slow_query_count": 0,
            "has_recommendations": False,
        })
        resp = await client.get("/performance?project_id=proj-abc&cluster_name=shipsafe-cluster")
        assert resp.status_code == 200
        assert "has_recommendations" in resp.json()

    @pytest.mark.asyncio
    async def test_performance_missing_project_id_returns_400(self, client):
        import agent.server as server_module
        import os
        env_bak = os.environ.pop("ATLAS_PROJECT_ID", None)
        try:
            resp = await client.get("/performance")
            assert resp.status_code == 400
        finally:
            if env_bak:
                os.environ["ATLAS_PROJECT_ID"] = env_bak

    @pytest.mark.asyncio
    async def test_orchestrator_not_ready_returns_503(self, client):
        import agent.server as server_module
        orig = server_module._orchestrator
        server_module._orchestrator = None
        try:
            resp = await client.post("/run", json={
                "event_id": "e1", "event_type": "closure",
                "vessels_affected": [], "severity": "LOW",
            })
            assert resp.status_code == 503
        finally:
            server_module._orchestrator = orig
