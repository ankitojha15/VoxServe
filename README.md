# VoxServe on MCP Hub — Voice + Text Support Copilot

VoxServe is a **voice + text AI support copilot** for e-commerce. It checks live orders, creates tickets, answers policy questions with citations, and hands off to a human when it isn't sure. Every action runs through MCP tools — the bot never touches data directly.

**Live demo:** https://voxserve.onrender.com/

[![eval-gate](https://github.com/ankitojha15/VoxServe/actions/workflows/eval.yml/badge.svg)](https://github.com/ankitojha15/VoxServe/actions)

> Note: hosted on a free tier — the service sleeps after idle, so the first request can take up to ~50s. Hit once, then use normally.

## Try it live

Open https://voxserve.onrender.com/ — no login needed. Four tabs: **Chat · Docs · Voice · Ops**.

Try these:

- `Where is my order 1001?` — live order status (demo IDs: `1001` shipped · `1002` delivered · `1003` stuck · `9999` not found)
- `How many days for COD refund?` — policy answer with `[FILE page X]` citation
- `Can I cancel after dispatch?` — return-policy reasoning
- Upload a policy PDF in **Docs**, then ask questions from it
- Press **Sound: On** to hear answers in a neural en-IN voice

## What it does

- **Multi-source ingestion** — policy docs (`.md` + `.pdf`, including user uploads) and past tickets, chunked into pgvector with `source + page` on every chunk
- **Hybrid retrieval** — dense embeddings + BM25 + rerank (cross-encoder locally, RRF/Cohere option on deploy), top-4 with citations; separate `vox_policy` / `vox_tickets` collections routed by intent
- **LangGraph agent** — `intent → retriever → tool-router → responder`; anything under 0.7 confidence escalates to a human instead of guessing
- **MCP Hub** — `order-mcp` (`get_order_status`, `get_policy`), `ticket-mcp` (`create_ticket`, `search_past_tickets`) with API-key auth and an audit log on every call
- **Voice** — browser mic + LiveKit room; answers spoken via neural TTS (`POST /voice/speak`, en-IN voice) with browser fallback; 2 missed turns auto-create a ticket
- **Prod** — FastAPI (chat, streaming, ingest, voice, health), exact + semantic Redis cache (intent-guarded, versioned keys), Langfuse tracing, slim Docker image, eval-gated CI

## Architecture

```text
User (Text / Voice)
        ↓
  FastAPI (/chat, /chat/stream, /demo, /voice/token,
           /voice/speak, /ingest/pdf, /sources, /health)
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
     Response (+ citation / handoff / audio)
         │
    ┌────┴────┐
  Redis     Langfuse
(2-level)   (trace + cost)
```

## API quick reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/` , `/demo` | GET | Support console UI |
| `/health` | GET | API + Redis status |
| `/chat` | POST | `{"query": "..."}` → answer, intent, confidence, citation |
| `/chat/stream` | POST | Same answer as server-sent events |
| `/voice/token` | POST | LiveKit room token |
| `/voice/speak` | POST | `{"text": "..."}` → neural-voice MP3 |
| `/ingest/pdf` | POST | Upload a policy PDF (multipart `file`) → chunked into search |
| `/sources` | GET | List ingested policy files |
| `/ingest/file?name=` | DELETE | Remove a file and rebuild search |
| `/admin/ingest?key=` | GET | Full re-ingest (API-key protected) |

## Eval — 60 tests, CI green

Golden regression set (n=50) plus 10 adversarial cases (typos, CAPS, Hindi-mix, punctuation). CI runs the full suite on every push; full history in `docs/eval-baseline.md`.

| Metric | Golden (n=50) | Extended (n=60) | RRF deploy | Target |
| Tool Acc | 50/50 = 1.00 | 59/60 = 0.98 | 59/60 = 0.98 | 0.91 |
| Faithfulness | 50/50 = 1.00 | 59/60 = 0.98 | 55/60 = 0.92 | 0.92 |
| Unsafe Block | 7/7 = 1.00 | 7/7 = 1.00 | 4/4 = 1.00 | 1.00 |
| p95 text | 0.08s local | 0.13s local | 0.04s local | 1.5s prod |
| Voice first-audio | 1.18s local file-TTS | — | 1.1s prod stream |
| Cost | $0.002/query est | — | $0.002 |

One documented gap: Hindi-mix `deliver kab hoga 1002?` routes to policy instead of order (keyword limit; fix is an LLM intent classifier). Held-out + real-traffic evals are the honest next step.

## Run locally

```bash
docker compose up -d        # pgvector + redis (+ backend image)
python -m backend.ingest    # policy chunks + tickets, idempotent
uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000/demo` — chat, streaming, mic, room join, and `(cached)` flags included.

## Deploy (Render, free tier)

Docker Blueprint via `render.yaml` (web + Postgres + Redis). Required env vars on the dashboard — secrets stay out of the repo (`.env.example` is the template):

- `DATABASE_URL`, `REDIS_URL` (wired from Render services)
- `EMBED_PROVIDER=api`, `EMBED_MODEL`, `HF_TOKEN` (torch-free embeddings)
- `RERANK_PROVIDER` (`rrf` on small instances), `GROQ_API_KEY`
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (voice room)
- `MCP_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`

## Tech Stack

**Python · LangChain · LangGraph · FastAPI · PostgreSQL + pgvector · Redis · FastMCP · LiveKit · Groq · edge-tts · Langfuse · Docker · Render**

## Safety

* Confidence-based human escalation (< 0.7)
* MCP-only data access with API-key auth and audit logging
* Secrets stay in `.env` / dashboard (never committed); `.env.example` is the template
* Voice fail-safe: 2 misses → auto-ticket
