import asyncio
import math
import time
from collections import OrderedDict

import httpx
import logfire

from app.config import settings
from app.httpclient import http_client

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
BATCH_SIZE = 64
MAX_ATTEMPTS = 6
_QUERY_CACHE_LIMIT = 512
_query_cache: OrderedDict[str, list[float]] = OrderedDict()


class EmbeddingUnavailable(RuntimeError):
    pass


def _model_path() -> str:
    model = settings.embedding_model
    return model if model.startswith("models/") else f"models/{model}"


def _headers() -> dict[str, str]:
    if not settings.gemini_api_key:
        raise EmbeddingUnavailable("GEMINI_API_KEY is not configured.")
    return {"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"}


def _request(text: str, task_type: str) -> dict:
    return {
        "model": _model_path(),
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": settings.embedding_dim,
    }


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


async def embed_query(text: str) -> list[float]:
    key = text.strip().lower()
    if key in _query_cache:
        _query_cache.move_to_end(key)
        return _query_cache[key]

    for attempt in range(3):
        response = await http_client().post(
            f"{API_ROOT}/{_model_path()}:embedContent",
            headers=_headers(),
            json=_request(text, "RETRIEVAL_QUERY"),
            timeout=10,
        )
        if response.status_code == 429 and attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))
            continue
        response.raise_for_status()
        vector = _normalize(response.json()["embedding"]["values"])
        _query_cache[key] = vector
        if len(_query_cache) > _QUERY_CACHE_LIMIT:
            _query_cache.popitem(last=False)
        return vector
    raise EmbeddingUnavailable("Embedding request was rate limited.")


def embed_documents(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    with httpx.Client(timeout=60) as client:
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            payload = {"requests": [_request(t, "RETRIEVAL_DOCUMENT") for t in batch]}
            for attempt in range(MAX_ATTEMPTS):
                response = client.post(
                    f"{API_ROOT}/{_model_path()}:batchEmbedContents", headers=_headers(), json=payload
                )
                if response.status_code == 429 and attempt < MAX_ATTEMPTS - 1:
                    wait = 2 ** (attempt + 1)
                    logfire.warn("embed.rate_limited", wait_seconds=wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                vectors.extend(_normalize(e["values"]) for e in response.json()["embeddings"])
                break
    return vectors
