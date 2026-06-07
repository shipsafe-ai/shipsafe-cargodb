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
        with patch.object(recall, "mcp_client") as mock_mcp, \
             patch("agent.specialists.memory_recall._embed_query") as mock_embed:
            mock_embed.return_value = [0.1] * 1024
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
        with patch.object(recall, "mcp_client") as mock_mcp, \
             patch("agent.specialists.memory_recall._embed_query") as mock_embed:
            mock_embed.return_value = [0.1] * 1024
            mock_mcp.aggregate = AsyncMock(return_value=[])
            await recall.find_similar("test query", top_k=3)
            call_args = mock_mcp.aggregate.call_args
            pipeline = call_args[1].get("pipeline") or call_args[0][0]
            stages = [list(s.keys())[0] for s in pipeline]
            assert "$vectorSearch" in stages

    @pytest.mark.asyncio
    async def test_recall_top_k_respected(self, recall):
        with patch.object(recall, "mcp_client") as mock_mcp, \
             patch("agent.specialists.memory_recall._embed_query") as mock_embed:
            mock_embed.return_value = [0.1] * 1024
            mock_mcp.aggregate = AsyncMock(return_value=[])
            await recall.find_similar("query", top_k=7)
            call_args = mock_mcp.aggregate.call_args
            pipeline = call_args[1].get("pipeline") or call_args[0][0]
            vs_stage = next(s for s in pipeline if "$vectorSearch" in s)
            assert vs_stage["$vectorSearch"]["limit"] == 7

    @pytest.mark.asyncio
    async def test_recall_filter_by_decision_type(self, recall, similar_doc):
        with patch.object(recall, "mcp_client") as mock_mcp, \
             patch("agent.specialists.memory_recall._embed_query") as mock_embed:
            mock_embed.return_value = [0.1] * 1024
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
    async def test_no_openai_in_recall(self, recall):
        """Recall must NOT use OpenAI. Voyage AI allowed for query embedding."""
        import inspect
        import agent.specialists.memory_recall as mod
        src = inspect.getsource(mod)
        assert "openai" not in src.lower()

    def test_embed_query_calls_voyage_api(self):
        """_embed_query must call Voyage AI endpoint and return 1024-dim vector."""
        import json
        from io import BytesIO
        from unittest.mock import patch, MagicMock
        from agent.specialists.memory_recall import _embed_query

        fake_resp = MagicMock()
        fake_resp.read.return_value = json.dumps(
            {"data": [{"embedding": [0.5] * 1024}]}
        ).encode()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=fake_resp), \
             patch("agent.specialists.memory_recall.get_secret", return_value="vk-test"):
            result = _embed_query("test query")
        assert len(result) == 1024
        assert result[0] == 0.5

    @pytest.mark.asyncio
    async def test_recall_embeds_query_before_vectorsearch(self, recall, similar_doc):
        """find_similar must embed query_text before building $vectorSearch."""
        with patch.object(recall, "mcp_client") as mock_mcp, \
             patch("agent.specialists.memory_recall._embed_query") as mock_embed:
            mock_embed.return_value = [0.1] * 1024
            mock_mcp.aggregate = AsyncMock(return_value=[similar_doc])
            await recall.find_similar("Hormuz closure", top_k=3)
            mock_embed.assert_called_once_with("Hormuz closure")
            call_args = mock_mcp.aggregate.call_args
            pipeline = call_args[1].get("pipeline") or call_args[0][0]
            vs = next(s for s in pipeline if "$vectorSearch" in s)
            assert isinstance(vs["$vectorSearch"]["queryVector"], list)
            assert len(vs["$vectorSearch"]["queryVector"]) == 1024
