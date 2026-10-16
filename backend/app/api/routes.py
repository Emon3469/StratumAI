from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.agents.graph import rag_agent
from app.api.chat import answer_chat, stream_chat
from app.api.rate_limit import rate_limit
from app.api.schemas import ChatRequest, ChatResponse, LegacyQueryRequest
from app.config import settings
from app.gateway import gateway
from app.services.retrieval.qdrant_service import collection_ready

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}


@router.get("/api/status", tags=["system"])
async def service_status() -> dict:
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "providers": gateway.status(),
        "fallback_order": [p.name for p in gateway.available()],
        "knowledge_base": {"collection": settings.qdrant_collection, "ready": await collection_ready()},
    }


@router.get("/api/models", tags=["chat"])
async def models() -> dict:
    return {"default": "auto", "providers": gateway.status()}


@router.post("/api/chat/stream", tags=["chat"], dependencies=[Depends(rate_limit)])
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(stream_chat(request), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/api/chat", tags=["chat"], response_model=ChatResponse, dependencies=[Depends(rate_limit)])
async def chat(request: ChatRequest) -> dict:
    return await answer_chat(request)


@router.post("/query", tags=["chat"], response_model=ChatResponse, include_in_schema=False)
async def legacy_query(request: LegacyQueryRequest) -> dict:
    return await answer_chat(ChatRequest(message=request.q))


@router.get("/graph", tags=["system"], response_class=PlainTextResponse)
async def graph() -> str:
    return rag_agent.get_graph().draw_mermaid()
