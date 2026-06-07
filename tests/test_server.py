"""Tests for FastAPI server endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

import agent.server as server_module
from agent.server import app


@pytest.fixture(autouse=True)
def mock_server_deps():
    """Inject mock specialists into server module globals."""
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

    server_module._orchestrator = mock_orchestrator
    server_module._recall = mock_recall
    server_module._harmonizer = mock_harmonizer
    server_module._pending = {}

    yield {
        "orchestrator": mock_orchestrator,
        "recall": mock_recall,
        "harmonizer": mock_harmonizer,
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
