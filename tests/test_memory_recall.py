"""RED tests for MemoryRecall — must fail before implementation."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def recall():
    from agent.specialists.memory_recall import MemoryRecall
    return MemoryRecall()


@pytest.fixture
def similar_doc():
    return {
        "_id": "abc123",
        "decision_id": "dec-redsea-2024",
        "decision_type": "routing",
        "decision_text": "Reroute via Cape of Good Hope due to Red Sea attacks",
        "outcome": "reroute_cape",
        "transit_time_delta_pct": 18.0,
        "score": 0.89,
        "timestamp": "2024-01-10T08:00:00Z",
    }


class TestMemoryRecallInit:
    def test_recall_has_mcp_client(self, recall):
        assert hasattr(recall, "mcp_client")

    def test_recall_uses_correct_index(self, recall):
        from agent.config import VECTOR_INDEX_NAME
        assert recall.vector_index == VECTOR_INDEX_NAME


class TestMemoryRecallQuery:
    @pytest.mark.asyncio
    async def test_recall_returns_similar_decisions(self, recall, similar_doc):
        with patch.object(recall, "mcp_client") as mock_mcp:
            mock_mcp.aggregate = AsyncMock(return_value=[similar_doc])
            results = await recall.find_similar(
                query_text="Hormuz closure, need reroute",
                decision_type="routing",
                top_k=5,
            )
            assert len(results) == 1
            assert results[0]["score"] >= 0.8

    @pytest.mark.asyncio
    async def test_recall_pipeline_uses_vector_search(self, recall):
        with patch.object(recall, "mcp_client") as mock_mcp:
            mock_mcp.aggregate = AsyncMock(return_value=[])
            await recall.find_similar("test query", top_k=3)
            call_args = mock_mcp.aggregate.call_args
            pipeline = call_args[1].get("pipeline") or call_args[0][0]
            stages = [list(s.keys())[0] for s in pipeline]
            assert "$vectorSearch" in stages

    @pytest.mark.asyncio
    async def test_recall_top_k_respected(self, recall):
        with patch.object(recall, "mcp_client") as mock_mcp:
            mock_mcp.aggregate = AsyncMock(return_value=[])
            await recall.find_similar("query", top_k=7)
            call_args = mock_mcp.aggregate.call_args
            pipeline = call_args[1].get("pipeline") or call_args[0][0]
            vs_stage = next(s for s in pipeline if "$vectorSearch" in s)
            assert vs_stage["$vectorSearch"]["limit"] == 7

    @pytest.mark.asyncio
    async def test_recall_filter_by_decision_type(self, recall, similar_doc):
        with patch.object(recall, "mcp_client") as mock_mcp:
            mock_mcp.aggregate = AsyncMock(return_value=[similar_doc])
            await recall.find_similar("query", decision_type="routing", top_k=5)
            call_args = mock_mcp.aggregate.call_args
            pipeline = call_args[1].get("pipeline") or call_args[0][0]
            vs_stage = next(s for s in pipeline if "$vectorSearch" in s)
            assert "filter" in vs_stage["$vectorSearch"]

    @pytest.mark.asyncio
    async def test_recall_empty_query_raises(self, recall):
        with pytest.raises(ValueError, match="query_text"):
            await recall.find_similar("", top_k=5)

    @pytest.mark.asyncio
    async def test_no_embedding_in_recall(self, recall):
        """MCP handles embedding. Recall must NOT call any embedding API."""
        import inspect
        import agent.specialists.memory_recall as mod
        src = inspect.getsource(mod)
        assert "openai" not in src.lower()
        assert "voyage" not in src.lower()
