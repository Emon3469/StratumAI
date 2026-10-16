import asyncio

from app.agents.nodes.events import emit, status
from app.agents.prompts import CONVERSATIONAL_SYSTEM, GENERAL_SYSTEM, RESPONDER_SYSTEM
from app.agents.state import AgentState
from app.config import settings
from app.gateway import StreamStart, gateway


def _build_messages(state: AgentState) -> list[dict[str, str]]:
    intent = state.get("intent")
    technical = intent == "technical" and state.get("use_knowledge_base", True)
    if technical:
        system = RESPONDER_SYSTEM
    elif intent == "technical":
        system = GENERAL_SYSTEM
    else:
        system = CONVERSATIONAL_SYSTEM
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for turn in state.get("history", [])[-settings.max_history_messages :]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    if technical:
        context = state.get("context") or "No relevant passages were found in the knowledge base."
        messages.append(
            {
                "role": "user",
                "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{state['question']}",
            }
        )
    else:
        messages.append({"role": "user", "content": state["question"]})
    return messages


async def respond_node(state: AgentState) -> dict:
    status("generating", "Writing the answer")
    parts: list[str] = []
    meta: StreamStart | None = None

    regenerate = bool(state.get("regenerate"))
    async for item in gateway.stream(
        _build_messages(state),
        preferred=state.get("preferred_provider"),
        temperature=0.7 if regenerate else 0.2,
        use_cache=not regenerate,
    ):
        if isinstance(item, StreamStart):
            meta = item
            emit("model", provider=item.provider, model=item.model, cached=item.cached, fallbacks=item.fallbacks)
            continue
        parts.append(item)
        emit("token", content=item)

    plan = [f"Model: {meta.provider}/{meta.model}" + (" (cache)" if meta.cached else "")] if meta else []
    return {
        "answer": "".join(parts),
        "provider": meta.provider if meta else None,
        "model": meta.model if meta else None,
        "cached": bool(meta and meta.cached),
        "fallbacks": meta.fallbacks if meta else 0,
        "plan": plan,
    }


async def refuse_node(state: AgentState) -> dict:
    message = state.get("refusal") or ""
    emit("model", provider="guardrails", model="policy", cached=False, fallbacks=0)
    words = message.split(" ")
    for index, word in enumerate(words):
        emit("token", content=word if index == 0 else f" {word}")
        await asyncio.sleep(0.008)
    return {"answer": message, "provider": "guardrails", "model": "policy", "cached": False, "fallbacks": 0}
