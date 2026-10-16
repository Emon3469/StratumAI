import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import logfire

from app.agents.graph import rag_agent
from app.agents.state import AgentState
from app.api.schemas import ChatRequest
from app.gateway import GatewayError

FAILURE_MESSAGE = (
    "I couldn't reach any of the configured language models just now. "
    "Please try again in a few seconds."
)


def initial_state(request: ChatRequest) -> AgentState:
    return {
        "question": request.message,
        "history": [turn.model_dump() for turn in request.history],
        "preferred_provider": request.provider,
        "use_knowledge_base": request.use_knowledge_base,
        "regenerate": request.regenerate,
        "plan": [],
        "sources": [],
    }


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_events(request: ChatRequest) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    started = time.perf_counter()
    first_token_ms: int | None = None
    final: dict[str, Any] = {"plan": []}

    try:
        async for mode, chunk in rag_agent.astream(initial_state(request), stream_mode=["custom", "updates"]):
            if mode == "custom":
                if chunk["event"] == "token" and first_token_ms is None:
                    first_token_ms = int((time.perf_counter() - started) * 1000)
                yield chunk["event"], chunk["data"]
                continue
            for update in chunk.values():
                if not update:
                    continue
                for key, value in update.items():
                    if key == "plan":
                        final["plan"].extend(value)
                    else:
                        final[key] = value
    except GatewayError as error:
        logfire.error("chat.gateway_failed", attempts=error.attempts)
        yield "error", {"message": FAILURE_MESSAGE, "attempts": [a["provider"] for a in error.attempts]}
        return

    yield "done", {
        "intent": final.get("intent"),
        "plan": final["plan"],
        "provider": final.get("provider"),
        "model": final.get("model"),
        "cached": final.get("cached", False),
        "fallbacks": final.get("fallbacks", 0),
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "ttft_ms": first_token_ms,
        "answer_chars": len(final.get("answer", "")),
        "_answer": final.get("answer", ""),
        "_sources": final.get("sources", []),
    }


async def stream_chat(request: ChatRequest) -> AsyncIterator[str]:
    request_id = uuid.uuid4().hex[:12]
    yield sse("ready", {"request_id": request_id})
    try:
        async for event, data in run_events(request):
            if event == "done":
                data = {k: v for k, v in data.items() if not k.startswith("_")}
            yield sse(event, data)
    except Exception as error:
        logfire.exception("chat.stream_failed", request_id=request_id)
        yield sse("error", {"message": "Something went wrong while generating the answer.", "detail": type(error).__name__})


async def answer_chat(request: ChatRequest) -> dict[str, Any]:
    tokens: list[str] = []
    done: dict[str, Any] = {}
    error: dict[str, Any] | None = None
    async for event, data in run_events(request):
        if event == "token":
            tokens.append(data["content"])
        elif event == "done":
            done = data
        elif event == "error":
            error = data

    sources = [
        {
            "id": s["id"],
            "source": s["source"],
            "source_type": s["source_type"],
            "score": s["score"],
            "snippet": s["text"][:280],
        }
        for s in done.get("_sources", [])
    ]
    return {
        "question": request.message,
        "answer": done.get("_answer") or "".join(tokens) or (error or {}).get("message", FAILURE_MESSAGE),
        "intent": done.get("intent"),
        "thought_process": done.get("plan", []),
        "status": "error" if error else "ok",
        "sources": sources,
        "provider": done.get("provider"),
        "model": done.get("model"),
        "latency_ms": done.get("latency_ms", 0),
    }
