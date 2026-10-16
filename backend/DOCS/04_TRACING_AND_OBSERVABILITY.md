# Tracing and Observability

## Logfire

Set `LOGFIRE_TOKEN` to send traces to Pydantic Logfire. Without a token nothing is exported.

Instrumented:

- every FastAPI request (health checks excluded)
- `llm.complete` spans per provider call and `llm.first_token` events with time to first token
- `llm.fallback` warnings with the provider and error when the gateway moves to the next provider
- `qdrant.search` and `rerank` spans
- guardrail blocks with category, layer and classifier score

## Per-response telemetry

Every streamed answer ends with a `done` event, shown under the message in the UI:

```json
{
  "intent": "technical",
  "plan": ["Guardrail: passed", "Intent: technical", "Search query: ...", "Retrieved 12 candidates, kept 5 after reranking", "Model: groq/openai/gpt-oss-120b"],
  "provider": "groq",
  "model": "openai/gpt-oss-120b",
  "cached": false,
  "fallbacks": 0,
  "latency_ms": 2140,
  "ttft_ms": 610
}
```

## Health endpoints

- `GET /health` is a constant-time liveness probe used by Render.
- `GET /api/status` reports configured providers, their cooldown state, the fallback order and whether the Qdrant collection has data.
