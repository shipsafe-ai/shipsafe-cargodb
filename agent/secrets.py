"""GCP Secret Manager accessor — rule 5: no hardcoded credentials."""
from __future__ import annotations
import functools
import os

from agent.config import GCP_PROJECT


@functools.lru_cache(maxsize=32)
def get_secret(name: str) -> str:
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/{GCP_PROJECT}/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": path})
    return response.payload.data.decode("UTF-8")
