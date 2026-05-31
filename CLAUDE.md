# CLAUDE.md — shipsafe-cargodb (MongoDB track)

This is the CargoDB submission repo. Read this file fully before
writing any code. Then read PARTNER-INTEGRATION.md §1.

---

## What CargoDB does

CargoDB gives AI agents persistent semantic memory. It stores every
agent decision with Voyage AI embeddings via the MongoDB MCP, and
recalls similar past decisions using Atlas Vector Search.
"Have we seen this before?" becomes a real query, not a mock string.

Universal value: any AI agent that benefits from decision memory —
fraud agents, recommendation agents, customer support agents.

---

## Agent specialists

| Specialist | File | Job |
|---|---|---|
| MemoryWriter | specialists/memory_writer.py | MCP insert-many; MCP auto-embeds via Voyage AI |
| MemoryRecall | specialists/memory_recall.py | MCP aggregate with $vectorSearch pipeline |
| SchemaHarmonizer | specialists/schema_harmonizer.py | MCP collection-schema (ONE feature, not the spine) |
| ManifestAuditor | specialists/manifest_auditor.py | MCP find + aggregate |
| MigrationGuardian | specialists/migration_guardian.py | MCP explain for index-impact safety |
| Critic | critic.py | Challenges above + prompt-injection check |

Orchestrator: orchestrator.py (ADK SequentialAgent)

---

## MongoDB integration (see PARTNER-INTEGRATION.md §1)

MCP server: mongodb-mcp-server (official)
Atlas cluster: shipsafe-cluster (GCP Mumbai, M0 free tier)
Database: cargodb_memory, Collection: decisions

CRITICAL GAP — Vector Search is PREVIEW:
Set MDB_MCP_PREVIEW_FEATURES=search on the MCP server env.
Without this flag, vector search tools are silently absent.
Smoke test: ask Claude Code to "create a vector search index" —
if MCP refuses, the flag is missing.

Auto-embedding: configure MCP server with VOYAGE_API_KEY and
insert-many auto-embeds text fields. Zero embedding code in
this repo. Do NOT use OpenAI embeddings (rules violation).
Voyage AI is allowed ONLY on this MongoDB track.

Vector Search index: decisions_vector_idx, 1024-dim (voyage-3.5-lite),
cosine similarity, filter fields: decision_type + timestamp.

---

## Secrets required

- MONGODB_ATLAS_URI — already in Secret Manager ✅
- VOYAGE_API_KEY — already in Secret Manager ✅
- MDB_MCP_PREVIEW_FEATURES=search — set as env var on MCP server

---

## Demo scenario

Hormuz Crisis unfolds. CargoDB writes each routing decision to
Atlas with Voyage AI embeddings. On the next decision, MemoryRecall
hits Vector Search and surfaces: "this matches the 2024 Red Sea
incident, 89% similar. Outcome: reroute via Cape of Good Hope,
+18% transit time." Real Vector Search, not a mocked string.

---

## Build day: Day 5 (June 2)

Warm-up: load sample_mflix dataset via Atlas UI and run a
$vectorSearch against it before writing agent code. Confirms
wiring works before adding Hormuz fixtures.

---

## Cross-cutting rules (from shipsafe-shared/CLAUDE.md — all 9 apply here)

1. ALL LLM calls use Gemini via Vertex AI ONLY. Voyage AI for
   embeddings on this track only (MongoDB-provided). NOT OpenAI.

2. Agent brains are Python ADK on Cloud Run. No low-code Agent Builder.

3. Deep MCP integration — Atlas MCP server with Vector Search.
   See PARTNER-INTEGRATION.md §1.

4. All deployments target Google Cloud Run only.

5. Every credential in GCP Secret Manager. Nothing hardcoded.

6. TDD always. Test file exists and FAILS before implementation.

7. Gemini model from config, never hardcoded.

8. CROSS-SUBMISSION ISOLATION. CargoDB's Atlas Vector Search is
   demonstrated within CargoDB alone. No /memory/similar HTTP
   endpoint exposed to other submissions.

9. PROMPT-INJECTION DEFENSE. Structured output. Human approval gate.

Full canonical rules: https://github.com/shipsafe-ai/shipsafe-shared/blob/main/CLAUDE.md
Full partner spec: https://github.com/shipsafe-ai/shipsafe-shared/blob/main/docs/PARTNER-INTEGRATION.md
