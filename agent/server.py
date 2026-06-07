"""CargoDB FastAPI server."""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.orchestrator import CargoDborchestrator
from agent.specialists.memory_recall import MemoryRecall
from agent.specialists.schema_harmonizer import SchemaHarmonizer
from agent.specialists.index_manager import IndexManager
from agent.specialists.performance_advisor import PerformanceAdvisor
from agent.config import MONGODB_DB, MONGODB_COLLECTION

_orchestrator: Optional[CargoDborchestrator] = None
_recall: Optional[MemoryRecall] = None
_harmonizer: Optional[SchemaHarmonizer] = None
_index_manager: Optional[IndexManager] = None
_perf_advisor: Optional[PerformanceAdvisor] = None

_pending: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator, _recall, _harmonizer, _index_manager, _perf_advisor
    _orchestrator = CargoDborchestrator()
    _recall = MemoryRecall()
    _harmonizer = SchemaHarmonizer()
    _index_manager = IndexManager()
    _perf_advisor = PerformanceAdvisor()
    # Ensure vector search index exists — idempotent
    try:
        await _index_manager.ensure_vector_index()
    except Exception:
        pass  # Log but don't block startup if Atlas unreachable
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


@app.get("/egress-ip")
async def egress_ip():
    """Return this container's outbound IP (for Atlas SA allowlist setup)."""
    import urllib.request
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5) as r:
            import json as _json
            return _json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


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
    candidate = pending["candidate_decision"]
    candidate["approved_by"] = payload.approver
    await _orchestrator.memory_writer.write(candidate)
    return {"decision_id": payload.decision_id, "status": "completed", "approver": payload.approver}


@app.get("/decisions")
async def list_decisions(decision_type: Optional[str] = None, limit: int = 20) -> dict:
    if _recall is None:
        raise HTTPException(503, "MemoryRecall not ready")
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


@app.get("/decisions/pending")
async def pending_decisions() -> dict:
    return {"pending": list(_pending.values()), "count": len(_pending)}


@app.get("/schema")
async def schema_report() -> dict:
    if _harmonizer is None:
        raise HTTPException(503, "SchemaHarmonizer not ready")
    return await _harmonizer.analyze()


@app.get("/indexes")
async def index_status() -> dict:
    if _index_manager is None:
        raise HTTPException(503, "IndexManager not ready")
    return await _index_manager.index_status()


@app.post("/indexes/ensure")
async def ensure_indexes() -> dict:
    if _index_manager is None:
        raise HTTPException(503, "IndexManager not ready")
    return await _index_manager.ensure_vector_index()


@app.get("/stats")
async def collection_stats() -> dict:
    if _perf_advisor is None:
        raise HTTPException(503, "PerformanceAdvisor not ready")
    return await _perf_advisor.get_collection_stats()


@app.get("/performance")
async def performance_recommendations(
    project_id: str = "",
    cluster_name: str = "shipsafe-cluster",
) -> dict:
    if _perf_advisor is None:
        raise HTTPException(503, "PerformanceAdvisor not ready")
    pid = project_id or os.environ.get("ATLAS_PROJECT_ID", "")
    if not pid:
        raise HTTPException(400, "project_id required (or set ATLAS_PROJECT_ID env var)")
    return await _perf_advisor.get_recommendations(project_id=pid, cluster_name=cluster_name)


@app.get("/alerts")
async def cluster_alerts(project_id: str = "") -> dict:
    if _perf_advisor is None:
        raise HTTPException(503, "PerformanceAdvisor not ready")
    pid = project_id or os.environ.get("ATLAS_PROJECT_ID", "")
    alerts = await _perf_advisor.get_cluster_alerts(project_id=pid)
    return {"alerts": alerts, "count": len(alerts)}
