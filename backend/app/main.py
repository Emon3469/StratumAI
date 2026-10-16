import threading
from contextlib import asynccontextmanager

import logfire

from app.config import settings

logfire.configure(
    token=settings.logfire_token,
    service_name="stratumai-api",
    environment=settings.environment,
    send_to_logfire="if-token-present",
    console=False,
)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.httpclient import close_http_client
from app.services.retrieval.ranking_service import warm_up


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=warm_up, daemon=True).start()
    yield
    await close_http_client()


app = FastAPI(
    title="StratumAI API",
    description="Agentic RAG backend with guardrails, multi-provider LLM fallback and streaming responses.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.allowed_origin_regex or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
    max_age=86400,
)

logfire.instrument_fastapi(app, excluded_urls="/health")


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    first = error.errors()[0] if error.errors() else {}
    return JSONResponse(
        status_code=422,
        content={"detail": first.get("msg", "Invalid request."), "field": ".".join(map(str, first.get("loc", [])))},
    )


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"name": "StratumAI API", "docs": "/docs", "health": "/health"}


app.include_router(router)
