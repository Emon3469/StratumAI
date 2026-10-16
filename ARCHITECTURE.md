# StratumAI Architecture

```mermaid
graph LR
    subgraph WEB ["Frontend · Next.js on Vercel"]
        UI["Chat UI<br/>streaming · sources · side threads"]
    end

    subgraph API ["Backend · FastAPI on Render"]
        EP["POST /api/chat/stream<br/>Server-Sent Events"]
        RL["Rate limiter + CORS"]
    end

    subgraph AGENT ["LangGraph agent"]
        AN["analyze<br/>guardrails ∥ planner"]
        RT["retrieve<br/>embed → search → rerank"]
        RS["respond<br/>token streaming"]
        RF["refuse<br/>policy reply"]
    end

    subgraph GUARD ["Guardrails"]
        PAT["Pattern rules"]
        PG["Prompt Guard 2<br/>classifier"]
    end

    subgraph RETRIEVAL ["Retrieval"]
        EMB["Gemini embeddings<br/>768-dim"]
        QD[("Qdrant Cloud")]
        FR["FlashRank<br/>cross-encoder"]
    end

    subgraph GW ["LLM gateway"]
        G["Fallback router<br/>cooldowns · TTL cache"]
        P1["Groq"]
        P2["OpenAI"]
        P3["Anthropic"]
        P4["Gemini"]
    end

    subgraph ING ["Offline ingestion"]
        LD["Loaders<br/>PDF · HTML · DOCX · PPTX · TXT"]
        CH["Chunker<br/>overlap"]
    end

    UI -->|SSE| EP
    EP --> RL --> AN
    AN --> PAT
    AN --> PG
    AN -->|technical| RT
    AN -->|conversational| RS
    AN -->|blocked / off-topic| RF
    RT --> EMB --> QD --> FR --> RS
    AN -->|plan| G
    RS -->|stream| G
    G --> P1
    G -.->|fallback| P2
    G -.->|fallback| P3
    G -.->|fallback| P4
    LD --> CH --> EMB
```

## Request lifecycle

1. The browser posts the message, recent history and model preference to `/api/chat/stream` and reads the Server-Sent Events stream.
2. `analyze` runs the input guardrails and the planner concurrently. The planner uses the gateway's fast model to classify intent and rewrite follow-ups into standalone search queries.
3. Technical questions go to `retrieve`: the query is embedded with Gemini, the top candidates are pulled from Qdrant and reranked locally with FlashRank. Sources are streamed to the client immediately.
4. `respond` streams the answer token by token through the gateway. The gateway walks the configured provider order and falls back on errors, rate limits or slow first tokens, putting failing providers into cooldown.
5. A final `done` event carries the plan, the provider and model that answered, latency and time to first token.

## Design choices

| Concern | Choice | Reason |
| --- | --- | --- |
| Latency | Guardrails and planner in parallel, pooled HTTP keep-alive, first-token timeout | Users see tokens in well under a second on Groq |
| Memory footprint | Provider calls over `httpx` instead of heavy SDKs | Starts in seconds and stays well inside Render's free 512 MB |
| Resilience | Ordered fallback across four providers with per-provider cooldowns | One expired key or rate limit never takes the app down |
| Statelessness | Client sends the recent history with each request | Survives restarts and free-tier sleep, scales horizontally |
| Grounding | Rerank before generation, numbered citations, source snippets in the UI | Answers can be verified against the knowledge base |
