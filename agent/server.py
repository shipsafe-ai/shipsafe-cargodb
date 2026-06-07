"""CargoDB FastAPI server — exposes /health /run /decisions /approve endpoints."""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.orchestrator import CargoDborchestrator
from agent.specialists.memory_recall import MemoryRecall
from agent.specialists.schema_harmonizer import SchemaHarmonizer
from agent.config import MONGODB_DB, MONGODB_COLLECTION

_orchestrator: Optional[CargoDborchestrator] = None
_recall: Optional[MemoryRecall] = None

# In-flight decisions awaiting human approval
_pending: dict[str, dict] = {}
_harmonizer: Optional[SchemaHarmonizer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator, _recall
    global _harmonizer
    _orchestrator = CargoDborchestrator()
    _recall = MemoryRecall()
    _harmonizer = SchemaHarmonizer()
    yield


app = FastAPI(title="CargoDB", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EventPayload(BaseModel):
    event_id: str
    event_type: str
    affected_strait: Optional[str] = None
    vessels_affected: list[str] = Field(default_factory=list)
    severity: str = "MEDIUM"
    timestamp: Optional[str] = None


class ApprovalPayload(BaseModel):
    decision_id: str
    approved: bool
    approver: str


class SimilarQuery(BaseModel):
    query_text: str
    decision_type: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cargodb", "db": MONGODB_DB}


@app.post("/run")
async def run_pipeline(payload: EventPayload) -> dict:
    if _orchestrator is None:
        raise HTTPException(503, "Orchestrator not ready")
    result = await _orchestrator.run(payload.model_dump())
    decision_id = result["decision_id"]
    if result["status"] == "pending_approval":
        _pending[decision_id] = result
    return result


@app.post("/approve")
async def approve_decision(payload: ApprovalPayload) -> dict:
    if payload.decision_id not in _pending:
        raise HTTPException(404, f"Decision {payload.decision_id} not found or already actioned")
    pending = _pending.pop(payload.decision_id)
    if not payload.approved:
        return {"decision_id": payload.decision_id, "status": "rejected", "approver": payload.approver}
    # Persist now that human approved
    candidate = pending["candidate_decision"]
    candidate["approved_by"] = payload.approver
    await _orchestrator.memory_writer.write(candidate)
    return {"decision_id": payload.decision_id, "status": "completed", "approver": payload.approver}


@app.get("/decisions")
async def list_decisions(decision_type: Optional[str] = None, limit: int = 20) -> dict:
    if _recall is None:
        raise HTTPException(503, "MemoryRecall not ready")
    # Return recent decisions via a broad vector search with a generic query
    results = await _recall.find_similar(
        query_text="routing decision reroute strait closure",
        decision_type=decision_type,
        top_k=limit,
    )
    return {"decisions": results, "count": len(results)}


@app.post("/decisions/similar")
async def similar_decisions(payload: SimilarQuery) -> dict:
    if _recall is None:
        raise HTTPException(503, "MemoryRecall not ready")
    results = await _recall.find_similar(
        query_text=payload.query_text,
        decision_type=payload.decision_type,
        top_k=payload.top_k,
    )
    return {"decisions": results, "count": len(results)}


@app.get("/schema")
async def schema_report() -> dict:
    if _harmonizer is None:
        raise HTTPException(503, "SchemaHarmonizer not ready")
    return await _harmonizer.analyze()


@app.get("/decisions/pending")
async def pending_decisions() -> dict:
    return {"pending": list(_pending.values()), "count": len(_pending)}
