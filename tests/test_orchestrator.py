"""RED tests for Orchestrator."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def orchestrator():
    from agent.orchestrator import CargoDborchestrator
    return CargoDborchestrator()


@pytest.fixture
def hormuz_event():
    return {
        "event_id": "evt-hormuz-001",
        "event_type": "strait_closure",
        "affected_strait": "Hormuz",
        "vessels_affected": ["vessel-hormuz-01", "vessel-hormuz-02"],
        "severity": "CRITICAL",
        "timestamp": "2024-06-01T00:00:00Z",
    }


class TestOrchestratorInit:
    def test_has_all_specialists(self, orchestrator):
        assert hasattr(orchestrator, "memory_writer")
        assert hasattr(orchestrator, "memory_recall")
        assert hasattr(orchestrator, "schema_harmonizer")
        assert hasattr(orchestrator, "manifest_auditor")
        assert hasattr(orchestrator, "migration_guardian")
        assert hasattr(orchestrator, "critic")

    def test_is_sequential_agent(self, orchestrator):
        from google.adk.agents import SequentialAgent
        assert isinstance(orchestrator, SequentialAgent)


class TestOrchestratorRun:
    @pytest.mark.asyncio
    async def test_run_full_pipeline(self, orchestrator, hormuz_event):
        with (
            patch.object(orchestrator.memory_recall, "find_similar", new_callable=AsyncMock) as mock_recall,
            patch.object(orchestrator.memory_writer, "write", new_callable=AsyncMock) as mock_write,
            patch.object(orchestrator.manifest_auditor, "audit", new_callable=AsyncMock) as mock_audit,
            patch.object(orchestrator.critic, "challenge", new_callable=AsyncMock) as mock_critic,
        ):
            mock_recall.return_value = [
                {
                    "decision_id": "dec-redsea-2024",
                    "score": 0.89,
                    "decision_text": "Reroute via Cape",
                    "outcome": "reroute_cape",
                }
            ]
            mock_audit.return_value = {"manifests": [], "by_status": {}}
            mock_critic.return_value = {
                "approved": True,
                "concerns": [],
                "risk_level": "LOW",
                "requires_human_approval": True,
            }
            mock_write.return_value = {"inserted_count": 1}

            result = await orchestrator.run(hormuz_event)
            assert result["status"] in ("pending_approval", "completed")
            assert "similar_decisions" in result
            assert "decision_id" in result

    @pytest.mark.asyncio
    async def test_similar_decisions_surfaced(self, orchestrator, hormuz_event):
        with (
            patch.object(orchestrator.memory_recall, "find_similar", new_callable=AsyncMock) as mock_recall,
            patch.object(orchestrator.memory_writer, "write", new_callable=AsyncMock),
            patch.object(orchestrator.manifest_auditor, "audit", new_callable=AsyncMock) as mock_audit,
            patch.object(orchestrator.critic, "challenge", new_callable=AsyncMock) as mock_critic,
        ):
            mock_recall.return_value = [{"decision_id": "dec-redsea-2024", "score": 0.89}]
            mock_audit.return_value = {"manifests": [], "by_status": {}}
            mock_critic.return_value = {
                "approved": True, "concerns": [], "risk_level": "LOW",
                "requires_human_approval": True,
            }
            result = await orchestrator.run(hormuz_event)
            assert len(result["similar_decisions"]) >= 1

    @pytest.mark.asyncio
    async def test_critic_blocks_auto_execution(self, orchestrator, hormuz_event):
        """Human gate: orchestrator must not execute if critic requires approval."""
        with (
            patch.object(orchestrator.memory_recall, "find_similar", new_callable=AsyncMock) as mock_recall,
            patch.object(orchestrator.memory_writer, "write", new_callable=AsyncMock),
            patch.object(orchestrator.manifest_auditor, "audit", new_callable=AsyncMock) as mock_audit,
            patch.object(orchestrator.critic, "challenge", new_callable=AsyncMock) as mock_critic,
        ):
            mock_recall.return_value = []
            mock_audit.return_value = {"manifests": [], "by_status": {}}
            mock_critic.return_value = {
                "approved": True, "concerns": [], "risk_level": "LOW",
                "requires_human_approval": True,
            }
            result = await orchestrator.run(hormuz_event)
            assert result["status"] == "pending_approval"
