# LLM Gateway

`app/gateway` is a small, dependency-light router that gives the agent one interface to four providers.

## Providers

| Provider | Transport | Default model |
| --- | --- | --- |
| Groq | OpenAI-compatible API | `openai/gpt-oss-120b`, backup `openai/gpt-oss-20b`, planner `qwen/qwen3.8-27b` |
| OpenAI | Chat Completions API | `gpt-4.1-mini`, fast `gpt-4.1-nano` |
| Anthropic | Messages API | `claude-haiku-4-5` |
| Gemini | OpenAI-compatible API | `gemini-flash-lite-latest`, backup `gemini-flash-latest` |

All calls share one pooled `httpx.AsyncClient`, so TLS connections are reused across requests.

## Routing

- **Targets**: every provider expands into one or more models, and each provider and model pair is a separate target with its own cooldown. Free-tier quotas are per model, so a rate-limited Groq model hands over to the next Groq model before leaving the provider. The planner uses a dedicated fast model so planning and answering never compete for the same quota.
- **Order**: `LLM_FALLBACK_ORDER`, limited to providers with a key. Picking a specific model in the UI moves that provider to the front; the rest remain as fallbacks.
- **Fallback triggers**: HTTP errors, timeouts, empty completions, or no first token within `LLM_FIRST_TOKEN_TIMEOUT_SECONDS`. A stream that fails after tokens were sent ends with an error event instead of mixing two answers.
- **Cooldowns**: invalid keys and exhausted credit cool down the whole provider for 10 minutes, unknown models only that model, rate limits for the provider's `retry-after` / reset window (capped at `LLM_COOLDOWN_SECONDS`), transient errors for 15 seconds. Cooling providers are tried last rather than skipped, so the app still answers when every provider is degraded.
- **Cache**: identical requests within `LLM_CACHE_TTL_SECONDS` are served from an in-memory LRU cache; cached streams are replayed in small chunks and flagged as cached.

## Interface

```python
from app.gateway import gateway

completion = await gateway.complete(messages, fast=True, json_mode=True)

async for item in gateway.stream(messages, preferred="openai"):
    ...
```

`stream` yields a `StreamStart` (provider, model, cached, fallbacks) followed by text deltas.

## Health

`GET /api/models` lists configured providers and whether each is currently healthy or cooling down.
