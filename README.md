# StratumAI

Agentic RAG assistant for engineering teams. Ask about Kubernetes workloads, infrastructure and systems, and get grounded answers streamed in real time with the sources they came from.

- **Frontend**: Next.js 16, React 19, Tailwind CSS 4, light and dark themes, streaming chat with citations, side threads on selected text, voice input and read-aloud
- **Backend**: FastAPI, LangGraph, Qdrant, Gemini embeddings, FlashRank reranking, layered guardrails
- **LLM gateway**: ordered fallback across Groq, OpenAI, Anthropic and Gemini with cooldowns and response caching

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Repository layout

```
StratumAI/
├── backend/            FastAPI service (deployed to Render)
│   ├── app/
│   │   ├── agents/     LangGraph graph, nodes and prompts
│   │   ├── api/        routes, SSE streaming, schemas, rate limiting
│   │   ├── gateway/    multi-provider LLM router with fallback
│   │   ├── guardrails/ input policies and injection classifier
│   │   ├── ingestion/  document loaders, chunking and indexing CLI
│   │   └── services/   embeddings, vector search, reranking
│   ├── DATA/           source documents
│   ├── DOCS/           design notes
│   └── evals/          golden dataset
├── frontend/           Next.js app (deployed to Vercel)
└── render.yaml         Render blueprint
```

## Running locally

Requirements: Python 3.12+, Node.js 20+.

1. Copy `.env.example` to `.env` in the repository root and fill in the keys.
2. Start the API:

   ```bash
   cd backend
   python -m venv .venv
   .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
   pip install -r requirements-ingest.txt
   uvicorn app.main:app --reload --port 8000
   ```

3. Index the knowledge base (first run only, or after adding documents):

   ```bash
   python -m app.ingestion.processor DATA/true_data --recreate
   ```

4. Start the web app:

   ```bash
   cd frontend
   cp .env.example .env.local
   npm install
   npm run dev
   ```

Open http://localhost:3000. Interactive API docs are at http://localhost:8000/docs.

## Testing

Backend unit and API tests run offline with stubbed providers:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

End-to-end tests against the real providers, Qdrant and embeddings:

```bash
pytest -m live
```

Check every configured model, the fallback chain, guardrails and retrieval in one report:

```bash
python -m scripts.check_connections
```

Simulate concurrent users against a running server:

```bash
python -m scripts.load_test --url http://127.0.0.1:8000 --users 8
```

Frontend unit tests, type checking and lint:

```bash
cd frontend
npm test
npm run typecheck
npm run lint
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/chat/stream` | Streamed answer as Server-Sent Events |
| `POST` | `/api/chat` | Same pipeline, single JSON response |
| `GET` | `/api/models` | Configured providers and their health |
| `GET` | `/api/status` | Providers, fallback order and knowledge base readiness |
| `GET` | `/health` | Liveness probe |
| `GET` | `/graph` | Mermaid diagram of the agent graph |

Stream events: `ready`, `status`, `sources`, `model`, `token`, `done`, `error`.

## Configuration

All settings are environment variables, documented in [backend/DOCS/05_ENVIRONMENT_VARIABLES.md](backend/DOCS/05_ENVIRONMENT_VARIABLES.md). Only the providers with a key set are used, so the app runs with any subset of Groq, OpenAI, Anthropic and Gemini.

## Deployment

- Backend: Render web service from `render.yaml` (root directory `backend`).
- Frontend: Vercel project with root directory `frontend` and `NEXT_PUBLIC_API_URL` pointing at the Render URL.
