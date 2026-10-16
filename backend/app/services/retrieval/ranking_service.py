import asyncio
import os
import tempfile
import threading

import logfire
from flashrank import Ranker, RerankRequest

from app.services.retrieval.qdrant_service import RetrievedChunk

_ranker: Ranker | None = None
_lock = threading.Lock()


def get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        with _lock:
            if _ranker is None:
                cache_dir = os.getenv("FLASHRANK_CACHE_DIR", os.path.join(tempfile.gettempdir(), "flashrank"))
                _ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir=cache_dir, max_length=384)
    return _ranker


def warm_up() -> None:
    try:
        get_ranker()
    except Exception as error:
        logfire.warn("reranker.warmup_failed", error=str(error)[:160])


def _rerank(query: str, chunks: list[RetrievedChunk], top_n: int) -> list[RetrievedChunk]:
    passages = [{"id": i, "text": chunk.text} for i, chunk in enumerate(chunks)]
    results = get_ranker().rerank(RerankRequest(query=query, passages=passages))
    ranked: list[RetrievedChunk] = []
    for result in results[:top_n]:
        chunk = chunks[int(result["id"])]
        ranked.append(RetrievedChunk(chunk.text, chunk.source, chunk.source_type, float(result["score"])))
    return ranked


async def rerank(query: str, chunks: list[RetrievedChunk], top_n: int) -> list[RetrievedChunk]:
    if not chunks:
        return []
    try:
        with logfire.span("rerank", candidates=len(chunks), top_n=top_n):
            return await asyncio.to_thread(_rerank, query, chunks, top_n)
    except Exception as error:
        logfire.warn("rerank.failed", error=str(error)[:160])
        return chunks[:top_n]
