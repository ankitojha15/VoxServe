# VoxServe on MCP Hub — Voice + Text Support Copilot

VoxServe is a **voice + text AI support copilot** for e-commerce. It checks live orders, creates tickets, answers policy questions with citations, and hands off to a human when it isn't sure. Every action runs through MCP tools — the bot never touches data directly.

## Why this exists

Support teams drown in repeat tickets and slow replies. Plain chatbots hallucinate — they approve refunds the policy never allowed, and on voice calls they keep zero context. VoxServe fixes that with retrieval grounding, controlled tool calls, and confidence-based handoff.

## What it does

- **Multi-source ingestion** — help docs (txt + PDF), help URLs, and 5,000 past tickets (synthetic, seed-reproducible) chunked at 800/100 into pgvector with `source + page` on every chunk
- **Hybrid retrieval** — dense (BGE) + BM25 + cross-encoder rerank, top-4 with citations; two collections (`vox_policy`, `vox_tickets`) routed by intent so tickets can't drown out policy
- **LangGraph agent** — `intent → retriever → tool-router → responder`; anything under 0.7 confidence goes to `escalate_to_human`
- **MCP Hub** — `order-mcp` (`get_order_status`, `get_policy`), `ticket-mcp` (`create_ticket`, `search_past_tickets`) with API-key auth and an audit log on every call
- **Voice** — LiveKit room + mic in the browser, barge-in UX, Groq LLM, free TTS; 2 missed turns auto-create a ticket
- **Prod** — FastAPI `/chat` + `/chat/stream` (SSE), exact + semantic Redis cache, Langfuse tracing (v4), Docker Compose, eval-gated CI

## Architecture

```text
User (Text / Voice)
        ↓
      FastAPI (/chat, /chat/stream, /demo, /voice/token)
        ↓
     LangGraph (intent → retriever → tool-router → responder)
        ↓
  ┌──────┴────────┐
  │               │
RAG             MCP Hub (auth + audit)
  │               │
pgvector      order-mcp / ticket-mcp
BM25 + rerank
  │
  └──────┬────────┘
         ↓
     Response (+ citation / handoff)
         │
    ┌────┴────┐
  Redis     Langfuse
 (2-level)   (trace + cost)
```

## Eval — 60 tests, CI green

Golden regression set (n=50) plus 10 adversarial cases (typos, CAPS, Hindi-mix, punctuation). CI runs the full suite on every push; full history in `docs/eval-baseline.md`.

| Metric | Golden (n=50) | Extended (n=60) | Target |
| Tool Acc | 50/50 = 1.00 | 59/60 = 0.98 | 0.91 |
| Faithfulness | 50/50 = 1.00 | 59/60 = 0.98 | 0.92 |
| Unsafe Block | 7/7 = 1.00 | 7/7 = 1.00 | 1.00 |
| p95 text | 0.08s local | 0.13s local | 1.5s prod |
| Voice first-audio | 1.18s local file-TTS | — | 1.1s prod stream |
| Cost | $0.002/query est | — | $0.002 |

One documented gap: Hindi-mix `deliver kab hoga 1002?` routes to policy instead of order (keyword limit; fix is an LLM intent classifier). Held-out + real-traffic evals are the honest next step.

## Try it

```bash
docker compose up -d        # pgvector + redis (+ backend image)
python -m backend.ingest    # 6 policy chunks + 5000 tickets, idempotent
uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000/demo` — chat, streaming, mic, room join, and `(cached)` flags included.

## Tech Stack

**Python · LangChain · LangGraph · FastAPI · PostgreSQL + pgvector · Redis · FastMCP · LiveKit · Groq · Langfuse · Docker**

## Safety

* Confidence-based human escalation (< 0.7)
* MCP-only data access with API-key auth and audit logging
* Secrets stay in `.env` (never committed); `.env.example` is the template
* Voice fail-safe: 2 misses → auto-ticket
