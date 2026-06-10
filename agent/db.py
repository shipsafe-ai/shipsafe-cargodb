"""Direct Motor/pymongo client for fast dashboard queries.

MCP is for AI agent tool use — spawns a subprocess per call (12-14s).
This module bypasses MCP for simple CRUD the dashboard needs (<100ms).
"""
from __future__ import annotations

import os
from typing import Any

import motor.motor_asyncio

from agent.config import MONGODB_DB, MONGODB_COLLECTION
from agent.mcp_client import _encode_mongo_uri
from agent.secrets import get_secret

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None


def _get_uri() -> str:
    uri = os.environ.get("MONGODB_ATLAS_URI") or get_secret("MONGODB_ATLAS_URI")
    return _encode_mongo_uri(uri)


def get_collection() -> motor.motor_asyncio.AsyncIOMotorCollection:
    global _client
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(_get_uri(), serverSelectionTimeoutMS=10000)
    return _client[MONGODB_DB][MONGODB_COLLECTION]


def _serialize(doc: dict) -> dict:
    """Convert BSON types to JSON-serializable equivalents."""
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result[k] = {"$oid": str(v)}
        elif isinstance(v, list):
            result[k] = [_serialize(i) if isinstance(i, dict) else i for i in v]
        elif isinstance(v, dict):
            result[k] = _serialize(v)
        else:
            result[k] = v
    return result


async def list_decisions(limit: int = 20, decision_type: str | None = None) -> list[dict]:
    col = get_collection()
    filt: dict[str, Any] = {}
    if decision_type:
        filt["decision_type"] = decision_type
    cursor = col.find(filt, {"embedding": 0}).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_serialize(doc) for doc in docs]
