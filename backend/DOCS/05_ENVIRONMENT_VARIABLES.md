# Environment Variables

Settings are loaded with `pydantic-settings` from the process environment, then `.env` in the repository root, then `backend/.env`. Copy `.env.example` to start.

## Application

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` on Render |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated exact origins allowed by CORS |
| `ALLOWED_ORIGIN_REGEX` | `https://.*\.vercel\.app` | Regex for preview deployments; leave empty to disable |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per client IP per minute on chat endpoints, `0` disables |

## Language models

Only providers with a key are used. Placeholder values such as `YOUR_KEY` are ignored.

| Variable | Default | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | | Groq key, free tier available |
| `OPENAI_API_KEY` | | OpenAI key |
| `ANTHROPIC_API_KEY` | | Anthropic key |
| `GEMINI_API_KEY` | | Google AI Studio key, also used for embeddings |
| `LLM_FALLBACK_ORDER` | `groq,openai,anthropic,gemini` | Provider order for the Auto model |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Primary answer model |
| `GROQ_BACKUP_MODELS` | `openai/gpt-oss-20b` | Comma-separated Groq models tried next; each has its own rate-limit bucket |
| `GROQ_FAST_MODEL` | `qwen/qwen3.8-27b` | Planner model |
| `GROQ_GUARD_MODEL` | `meta-llama/llama-prompt-guard-2-86m` | Injection classifier |
| `OPENAI_MODEL` / `OPENAI_FAST_MODEL` | `gpt-4.1-mini` / `gpt-4.1-nano` | |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5` | |
| `GEMINI_MODEL` | `gemini-flash-lite-latest` | |
| `GEMINI_BACKUP_MODELS` | `gemini-flash-latest` | Comma-separated Gemini models tried next |
| `LLM_TIMEOUT_SECONDS` | `25` | Overall request timeout |
| `LLM_FIRST_TOKEN_TIMEOUT_SECONDS` | `12` | Fall back if no token arrives in time |
| `LLM_MAX_OUTPUT_TOKENS` | `1200` | Answer length cap |
| `LLM_COOLDOWN_SECONDS` | `20` | Upper bound for rate-limit cooldowns; the provider's reset header is used when present |
| `PLANNER_BUDGET_SECONDS` | `2.5` | Time allowed for intent planning before falling back to the raw question |
| `LLM_CACHE_TTL_SECONDS` / `LLM_CACHE_SIZE` | `900` / `256` | In-memory response cache |

## Guardrails

| Variable | Default | Description |
| --- | --- | --- |
| `GUARD_ENABLED` | `true` | Toggle input guardrails |
| `GUARD_THRESHOLD` | `0.85` | Classifier score at or above which a message is blocked |

## Retrieval

| Variable | Default | Description |
| --- | --- | --- |
| `QDRANT_CLUSTER_ENDPOINT` | | Qdrant Cloud URL, for example `https://xyz.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | | Qdrant API key |
| `QDRANT_COLLECTION` | `stratumai_kb` | Collection name |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini embedding model |
| `EMBEDDING_DIM` | `768` | Must match the collection; re-index after changing |
| `RETRIEVAL_CANDIDATES` / `RETRIEVAL_TOP_K` | `12` / `5` | Search depth and passages kept after reranking |
| `MAX_CONTEXT_CHARS` | `9000` | Context budget per answer |
| `FLASHRANK_CACHE_DIR` | system temp | Where the reranker model is cached |

## Observability

| Variable | Description |
| --- | --- |
| `LOGFIRE_TOKEN` | Optional Logfire write token |

## Frontend

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Base URL of the API, without a trailing slash |
