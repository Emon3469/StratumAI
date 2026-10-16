import logfire

from app.agents.nodes.events import emit, status
from app.agents.prompts import format_context
from app.agents.state import AgentState
from app.config import settings
from app.services.retrieval import embed_query, rerank, search


async def retrieve_node(state: AgentState) -> dict:
    query = state.get("search_query") or state["question"]
    status("retrieving", "Searching the knowledge base")

    try:
        vector = await embed_query(query)
        candidates = await search(vector, settings.retrieval_candidates)
        status("ranking", f"Ranking {len(candidates)} passages")
        ranked = await rerank(query, candidates, settings.retrieval_top_k)
    except Exception as error:
        logfire.error("retrieval.failed", error=str(error)[:200])
        emit("sources", items=[])
        return {"sources": [], "context": "", "plan": ["Retrieval: unavailable"]}

    passages: list[dict] = []
    budget = settings.max_context_chars
    for chunk in ranked:
        if budget <= 0:
            break
        text = chunk.text[:budget]
        budget -= len(text)
        passages.append(
            {
                "id": len(passages) + 1,
                "source": chunk.source,
                "source_type": chunk.source_type,
                "score": round(chunk.score, 4),
                "text": text,
            }
        )

    emit(
        "sources",
        items=[
            {
                "id": p["id"],
                "source": p["source"],
                "source_type": p["source_type"],
                "score": p["score"],
                "snippet": p["text"][:280],
            }
            for p in passages
        ],
    )
    return {
        "sources": passages,
        "context": format_context(passages),
        "plan": [f"Retrieved {len(candidates)} candidates, kept {len(passages)} after reranking"],
    }
