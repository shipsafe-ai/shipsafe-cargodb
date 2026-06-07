"""CargoDB agent configuration — all model/env refs live here."""
import os

# Gemini model from config — never hardcoded in logic (rule 7)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "shipsafe-ai")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")

MONGODB_DB = "cargodb_memory"
MONGODB_COLLECTION = "decisions"
VECTOR_INDEX_NAME = "decisions_vector_idx"
VECTOR_DIMENSIONS = 1024
VOYAGE_MODEL = "voyage-3.5-lite"
