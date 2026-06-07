"""Seed Atlas with historical decisions for Hormuz Crisis demo.

Run: python demo/seed_atlas.py [--with-embeddings]

--with-embeddings: also call Voyage AI to generate real 1024-dim embeddings
                   (requires VOYAGE_API_KEY env or Secret Manager access)
Without flag: inserts docs without embedding field (vector search won't work
              until Atlas auto-vectorization is configured or embeddings added).
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.mcp_client import _encode_mongo_uri
from agent.secrets import get_secret
from demo.hormuz_fixtures import HISTORICAL_DECISIONS

import pymongo


def get_atlas_client():
    raw = os.environ.get("MONGODB_ATLAS_URI") or get_secret("MONGODB_ATLAS_URI")
    uri = _encode_mongo_uri(raw)
    return pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)


def embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    """Call Voyage AI REST API directly — avoids any SDK dependency."""
    import json, urllib.request
    payload = json.dumps({
        "model": "voyage-3.5-lite",
        "input": texts,
    }).encode()
    req = urllib.request.Request(
        "https://api.voyageai.com/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return [item["embedding"] for item in data["data"]]


def seed(with_embeddings: bool = False):
    mc = get_atlas_client()
    db = mc["cargodb_memory"]
    col = db["decisions"]

    existing_ids = {d["decision_id"] for d in col.find({}, {"decision_id": 1})}
    to_insert = [d for d in HISTORICAL_DECISIONS if d["decision_id"] not in existing_ids]

    if not to_insert:
        print(f"All {len(HISTORICAL_DECISIONS)} decisions already seeded.")
        return

    if with_embeddings:
        voyage_key = os.environ.get("VOYAGE_API_KEY") or get_secret("VOYAGE_API_KEY")
        texts = [d["decision_text"] for d in to_insert]
        print(f"Generating embeddings for {len(texts)} decisions via Voyage AI...")
        embeddings = embed_texts(texts, voyage_key)
        for doc, emb in zip(to_insert, embeddings):
            doc["embedding"] = emb
        print(f"  Embeddings generated (dim={len(embeddings[0])})")

    result = col.insert_many(to_insert)
    print(f"Inserted {len(result.inserted_ids)} decisions into cargodb_memory.decisions")
    print(f"Total in collection: {col.count_documents({})}")

    if not with_embeddings:
        print("\nWARNING: No embeddings. $vectorSearch will return nothing.")
        print("Re-run with --with-embeddings to generate Voyage AI embeddings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-embeddings", action="store_true")
    args = parser.parse_args()
    seed(with_embeddings=args.with_embeddings)
