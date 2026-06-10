"""CargoDB Orchestrator — ADK SequentialAgent coordinating all specialists.

Pipeline per event:
  1. MemoryRecall      — Atlas Vector Search surfaces similar past decisions
  2. ManifestAuditor   — affected cargo manifests
  3. SchemaHarmonizer  — memory-collection schema-drift check (read-only)
  4. MigrationGuardian — recall-query index-safety check (read-only)
  5. DecisionReasoner  — Gemini reasons over precedents → action + rationale + chain-of-thought
  6. Critic            — Gemini adversarial challenge + injection detection + human gate
  7. MemoryWriter      — persist decision (only after gate opens)
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from google.adk.agents import SequentialAgent
from pydantic import ConfigDict, model_validator

from agent.specialists.memory_writer import MemoryWriter
from agent.specialists.memory_recall import MemoryRecall
from agent.specialists.schema_harmonizer import SchemaHarmonizer
from agent.specialists.manifest_auditor import ManifestAuditor
from agent.specialists.migration_guardian import MigrationGuardian
from agent.specialists.decision_reasoner import DecisionReasoner
from agent.critic import Critic


class CargoDborchestrator(SequentialAgent):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    memory_writer: Optional[Any] = None
    memory_recall: Optional[Any] = None
    schema_harmonizer: Optional[Any] = None
    manifest_auditor: Optional[Any] = None
    migration_guardian: Optional[Any] = None
    decision_reasoner: Optional[Any] = None
    critic: Optional[Any] = None

    def model_post_init(self, __context: Any) -> None:
        self.memory_writer = MemoryWriter()
        self.memory_recall = MemoryRecall()
        self.schema_harmonizer = SchemaHarmonizer()
        self.manifest_auditor = ManifestAuditor()
        self.migration_guardian = MigrationGuardian()
        self.decision_reasoner = DecisionReasoner()
        self.critic = Critic()

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("name", "CargoDB_Orchestrator")
        super().__init__(**kwargs)

    async def run(self, event: dict) -> dict:
        event_text = (
            f"{event.get('event_type', '')} affecting {event.get('affected_strait', '')}. "
            f"Severity: {event.get('severity', '')}. "
            f"Vessels: {', '.join(event.get('vessels_affected', []))}"
        )

        # 1. MemoryRecall — Atlas Vector Search surfaces similar past decisions
        similar = await self.memory_recall.find_similar(
            query_text=event_text,
            decision_type="routing",
            top_k=5,
        )

        # 2. ManifestAuditor — affected cargo manifests
        manifests_data = await self.manifest_auditor.audit()

        # 3. SchemaHarmonizer — flag memory-collection schema drift (read-only, non-blocking)
        try:
            schema_report = await self.schema_harmonizer.analyze()
        except Exception as exc:  # noqa: BLE001
            schema_report = {"error": str(exc)}

        # 4. MigrationGuardian — assess the recall query's index safety (read-only, non-blocking)
        try:
            migration_report = await self.migration_guardian.assess_index_impact(
                {"decision_type": "routing"}
            )
        except Exception as exc:  # noqa: BLE001
            migration_report = {"error": str(exc)}

        decision_id = f"dec-{uuid.uuid4().hex[:8]}"
        best_match = similar[0] if similar else None

        # Deterministic fallback (used if Gemini reasoning is unavailable)
        if best_match and best_match.get("score", 0) >= 0.75:
            recommended_action = best_match.get("outcome", "reroute_cape")
            confidence = best_match["score"]
            decision_text = (
                f"Based on {best_match['decision_id']} ({best_match['score']:.0%} similar): "
                f"{best_match.get('decision_text', 'Reroute via Cape of Good Hope')}"
            )
        else:
            recommended_action = "reroute_cape"
            confidence = 0.6
            decision_text = (
                f"No strong historical match. Recommend reroute via Cape of Good Hope "
                f"for {event.get('affected_strait')} closure."
            )

        # 5. DecisionReasoner — Gemini reasons over the recalled precedents (the brain).
        #    Produces the action + rationale + visible chain-of-thought; code fallback above.
        reasoning = await self.decision_reasoner.reason(
            event_text=event_text,
            precedents=similar,
            manifests=manifests_data,
        )
        rationale = ""
        decision_thinking = ""
        if reasoning and reasoning.get("recommended_action"):
            recommended_action = reasoning["recommended_action"]
            if isinstance(reasoning.get("confidence"), (int, float)):
                confidence = float(reasoning["confidence"])
            rationale = reasoning.get("rationale", "")
            decision_thinking = reasoning.get("thinking", "")
            if rationale:
                decision_text = rationale

        candidate = {
            "decision_id": decision_id,
            "decision_type": "routing",
            "decision_text": decision_text,
            "recommended_action": recommended_action,
            "confidence": confidence,
            "rationale": rationale,
            "decision_thinking": decision_thinking,
            "key_precedent": reasoning.get("key_precedent") if reasoning else None,
            "similar_past_decisions": similar,
            "event_id": event.get("event_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 6. Critic — Gemini adversarially challenges + human gate
        verdict = await self.critic.challenge(candidate)

        result: dict = {
            "decision_id": decision_id,
            "similar_decisions": similar,
            "candidate_decision": candidate,
            "schema_report": schema_report,
            "migration_report": migration_report,
            "verdict": verdict,
            "status": "pending_approval",
        }

        # 5. Persist only if human has approved
        if not verdict.get("requires_human_approval", True):
            await self.memory_writer.write(candidate)
            result["status"] = "completed"

        return result
