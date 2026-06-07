"""Tests for MongoMCPClient — mock MCP session layer."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def client():
    from agent.mcp_client import MongoMCPClient
    return MongoMCPClient(db_name="cargodb_memory", collection_name="decisions")


def _mock_session(return_value):
    """Build a mock MCP session context that returns given value from call_tool."""
    mock_result = MagicMock()
    mock_result.content = [MagicMock(text=json.dumps(return_value))]
    session = MagicMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=mock_result)
    return session


@pytest.fixture
def patch_session():
    """Context manager patcher for _mcp_session."""
    from contextlib import asynccontextmanager

    def make_patcher(return_value):
        session = _mock_session(return_value)

        @asynccontextmanager
        async def fake_session():
            yield session

        return patch("agent.mcp_client._mcp_session", fake_session), session

    return make_patcher


class TestInsertMany:
    @pytest.mark.asyncio
    async def test_insert_many_returns_ids(self, client, patch_session):
        patcher, session = patch_session({"insertedIds": {"0": "abc", "1": "def"}})
        with patcher:
            result = await client.insert_many(documents=[{"x": 1}, {"x": 2}])
        assert result["inserted_ids"] == ["abc", "def"]
        session.call_tool.assert_called_once_with(
            "insert-many",
            arguments={
                "database": "cargodb_memory",
                "collection": "decisions",
                "documents": [{"x": 1}, {"x": 2}],
            },
        )

    @pytest.mark.asyncio
    async def test_insert_many_empty_result(self, client, patch_session):
        patcher, _ = patch_session({})
        with patcher:
            result = await client.insert_many(documents=[])
        assert result["inserted_ids"] == []


class TestAggregate:
    @pytest.mark.asyncio
    async def test_aggregate_returns_list(self, client, patch_session):
        docs = [{"_id": "1", "score": 0.9}]
        patcher, _ = patch_session(docs)
        with patcher:
            result = await client.aggregate(pipeline=[{"$match": {}}])
        assert result == docs

    @pytest.mark.asyncio
    async def test_aggregate_dict_response(self, client, patch_session):
        patcher, _ = patch_session({"documents": [{"x": 1}]})
        with patcher:
            result = await client.aggregate(pipeline=[])
        assert result == [{"x": 1}]


class TestFind:
    @pytest.mark.asyncio
    async def test_find_returns_list(self, client, patch_session):
        docs = [{"vessel_id": "v-001"}]
        patcher, session = patch_session(docs)
        with patcher:
            result = await client.find(filter={"vessel_id": "v-001"}, limit=10)
        assert result == docs
        call_args = session.call_tool.call_args
        assert call_args[1]["arguments"]["limit"] == 10


class TestCollectionSchema:
    @pytest.mark.asyncio
    async def test_schema_returns_dict(self, client, patch_session):
        schema = {"fields": [{"name": "decision_id", "type": "string"}]}
        patcher, _ = patch_session(schema)
        with patcher:
            result = await client.collection_schema()
        assert result == schema


class TestCollectionIndexes:
    @pytest.mark.asyncio
    async def test_indexes_returns_list(self, client, patch_session):
        indexes = [{"name": "_id_"}, {"name": "decisions_vector_idx"}]
        patcher, _ = patch_session(indexes)
        with patcher:
            result = await client.collection_indexes()
        assert len(result) == 2


class TestCreateIndex:
    @pytest.mark.asyncio
    async def test_create_index_passes_keys_and_options(self, client, patch_session):
        patcher, session = patch_session({"ok": 1})
        with patcher:
            result = await client.create_index(
                keys={"embedding": "vectorSearch"},
                options={"name": "decisions_vector_idx"},
            )
        assert result == {"ok": 1}
        call_args = session.call_tool.call_args
        args = call_args[1]["arguments"]
        assert args["keys"] == {"embedding": "vectorSearch"}
        assert args["options"]["name"] == "decisions_vector_idx"


class TestCount:
    @pytest.mark.asyncio
    async def test_count_returns_int(self, client, patch_session):
        patcher, _ = patch_session({"count": 42})
        with patcher:
            result = await client.count()
        assert result == 42

    @pytest.mark.asyncio
    async def test_count_int_response(self, client, patch_session):
        from contextlib import asynccontextmanager
        session = _mock_session(42)
        session_content = MagicMock()
        session_content.content = [MagicMock(text="42")]
        session.call_tool = AsyncMock(return_value=session_content)

        @asynccontextmanager
        async def fake_session():
            yield session

        with patch("agent.mcp_client._mcp_session", fake_session):
            result = await client.count()
        assert result == 42


class TestExplain:
    @pytest.mark.asyncio
    async def test_explain_returns_plan(self, client, patch_session):
        plan = {"queryPlanner": {"winningPlan": {"stage": "IXSCAN"}}}
        patcher, session = patch_session(plan)
        with patcher:
            result = await client.explain(query={"decision_type": "routing"})
        assert result == plan
        call_args = session.call_tool.call_args
        assert call_args[1]["arguments"]["filter"] == {"decision_type": "routing"}


class TestAtlasTools:
    @pytest.mark.asyncio
    async def test_performance_advisor(self, client, patch_session):
        mock_resp = {"suggestedIndexes": [], "slowQueries": []}
        patcher, session = patch_session(mock_resp)
        with patcher:
            result = await client.atlas_performance_advisor(
                project_id="proj-123", cluster_name="shipsafe-cluster"
            )
        assert "suggestedIndexes" in result
        call_args = session.call_tool.call_args
        assert call_args[0][0] == "atlas-get-performance-advisor"

    @pytest.mark.asyncio
    async def test_atlas_list_alerts(self, client, patch_session):
        alerts = [{"id": "a-001", "status": "OPEN"}]
        patcher, session = patch_session(alerts)
        with patcher:
            result = await client.atlas_list_alerts(project_id="proj-123")
        assert result == alerts
        call_args = session.call_tool.call_args
        assert call_args[0][0] == "atlas-list-alerts"

    @pytest.mark.asyncio
    async def test_search_knowledge(self, client, patch_session):
        results = [{"title": "Vector Search Guide", "url": "https://mongodb.com/..."}]
        patcher, session = patch_session(results)
        with patcher:
            result = await client.search_knowledge(query="vector search index creation")
        assert result == results
        call_args = session.call_tool.call_args
        assert call_args[0][0] == "search-knowledge"


class TestEnvVarNames:
    def test_correct_mcp_env_vars_used(self):
        """MDB_MCP_CONNECTION_STRING and MDB_MCP_VOYAGE_API_KEY must be used."""
        import inspect
        import agent.mcp_client as mod
        src = inspect.getsource(mod)
        assert "MDB_MCP_CONNECTION_STRING" in src
        assert "MDB_MCP_VOYAGE_API_KEY" in src
        assert "MDB_CONNECTION_STRING" not in src.replace("MDB_MCP_CONNECTION_STRING", "")
