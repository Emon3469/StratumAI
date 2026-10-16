from dataclasses import dataclass

import logfire

from app.config import settings
from app.httpclient import http_client


@dataclass
class RetrievedChunk:
    text: str
    source: str
    source_type: str
    score: float


def _base() -> str:
    if not settings.qdrant_url:
        raise RuntimeError("QDRANT_CLUSTER_ENDPOINT is not configured.")
    return settings.qdrant_url.rstrip("/")


def _headers() -> dict[str, str]:
    return {"api-key": settings.qdrant_api_key or "", "Content-Type": "application/json"}


async def search(vector: list[float], limit: int) -> list[RetrievedChunk]:
    with logfire.span("qdrant.search", limit=limit):
        response = await http_client().post(
            f"{_base()}/collections/{settings.qdrant_collection}/points/query",
            headers=_headers(),
            json={"query": vector, "limit": limit, "with_payload": True},
            timeout=10,
        )
    response.raise_for_status()
    points = response.json().get("result", {}).get("points", [])
    return [
        RetrievedChunk(
            text=point["payload"].get("text", ""),
            source=point["payload"].get("source", "unknown"),
            source_type=point["payload"].get("source_type", "general"),
            score=float(point.get("score", 0.0)),
        )
        for point in points
        if point.get("payload")
    ]


async def collection_ready() -> bool:
    try:
        response = await http_client().get(
            f"{_base()}/collections/{settings.qdrant_collection}", headers=_headers(), timeout=5
        )
        if response.status_code != 200:
            return False
        return (response.json().get("result", {}).get("points_count") or 0) > 0
    except Exception:
        return False


def sync_client():
    from qdrant_client import QdrantClient

    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=60)


def ensure_collection(recreate: bool = False) -> None:
    from qdrant_client.http import models

    client = sync_client()
    name = settings.qdrant_collection
    if recreate and client.collection_exists(name):
        client.delete_collection(name)
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(size=settings.embedding_dim, distance=models.Distance.COSINE),
        )
        client.create_payload_index(name, "source", models.PayloadSchemaType.KEYWORD)
        client.create_payload_index(name, "source_type", models.PayloadSchemaType.KEYWORD)
