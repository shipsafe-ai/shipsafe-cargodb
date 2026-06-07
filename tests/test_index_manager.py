"""Tests for IndexManager."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def manager():
    from agent.specialists.index_manager import IndexManager
    return IndexManager()


class TestIndexManagerInit:
    def test_has_mcp_client(self, manager):
        assert hasattr(manager, "mcp_client")


class TestIndexManagerEnsure:
    @pytest.mark.asyncio
    async def test_creates_index_when_absent(self, manager):
        with patch.object(manager, "mcp_client") as mock_mcp:
            mock_mcp.collection_indexes = AsyncMock(return_value=[
                {"name": "some_other_index"}
            ])
            mock_mcp.create_index = AsyncMock(return_value={"ok": 1})
            result = await manager.ensure_vector_index()
            assert result["status"] == "created"
            mock_mcp.create_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_if_index_exists(self, manager):
        from agent.config import VECTOR_INDEX_NAME
        with patch.object(manager, "mcp_client") as mock_mcp:
            mock_mcp.collection_indexes = AsyncMock(return_value=[
                {"name": VECTOR_INDEX_NAME}
            ])
            mock_mcp.create_index = AsyncMock()
            result = await manager.ensure_vector_index()
            assert result["status"] == "exists"
            mock_mcp.create_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_status_reports_presence(self, manager):
        from agent.config import VECTOR_INDEX_NAME
        with patch.object(manager, "mcp_client") as mock_mcp:
            mock_mcp.collection_indexes = AsyncMock(return_value=[
                {"name": VECTOR_INDEX_NAME},
                {"name": "_id_"},
            ])
            status = await manager.index_status()
            assert status["vector_index_present"] is True
            assert status["total"] == 2

    @pytest.mark.asyncio
    async def test_index_status_reports_absent(self, manager):
        with patch.object(manager, "mcp_client") as mock_mcp:
            mock_mcp.collection_indexes = AsyncMock(return_value=[{"name": "_id_"}])
            status = await manager.index_status()
            assert status["vector_index_present"] is False
