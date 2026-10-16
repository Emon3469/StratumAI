# Known Gotchas and Decisions

## Embedding dimension must match the collection

The collection is created with `EMBEDDING_DIM`. Changing the model or dimension requires `--recreate` and a full re-index, otherwise Qdrant rejects queries with a dimension mismatch.

## Free-tier cold starts

Render's free instances sleep after inactivity and take up to a minute to wake. The web app pings `/health` on load, shows a "waking up" banner and keeps retrying, so the first message is not lost. The reranker model is warmed in a background thread at startup.

## Telemetry is configured first

`logfire.configure()` runs at the top of `app/main.py`, before the rest of the application is imported, so spans emitted during import are not dropped.

## Heavy SDKs are avoided at runtime

Provider calls, embeddings and Qdrant search use a shared `httpx.AsyncClient`. The official SDKs roughly tripled startup time and memory, which matters on a 512 MB instance. `qdrant-client` and the document parsers are only installed for ingestion (`requirements-ingest.txt`).

## Streaming through proxies

The stream endpoint sets `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no`, and no compression middleware is used, so tokens are not buffered by intermediaries.

## Reasoning models

`gpt-oss` models on Groq are called with `reasoning_effort: low`. Higher effort improves hard answers but adds noticeable latency before the first token.

## Conversation memory lives in the client

The browser sends recent turns with each request. The API holds no session state, so restarts and multiple instances behave the same.
