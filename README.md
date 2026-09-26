# VoxServe on MCP Hub — Voice + Text Support Copilot

VoxServe is a **voice + text AI support copilot** that can retrieve support information, check live orders, create tickets, and escalate uncertain requests to humans.

## 🚀 Features

* **Multi-source RAG** — PDFs, help URLs, and 5K past support tickets
* **Hybrid Retrieval** — Dense + BM25 + Cross-Encoder reranking
* **Citations** — Top-4 retrieved sources with `source + page` metadata
* **LangGraph Agent** — `intent → retriever → tool-router → responder`
* **MCP Tools** — Order status, policies, ticket creation, and past-ticket search
* **Human Handoff** — Requests with confidence `< 0.7` are escalated
* **Voice Support** — LiveKit with STT, VAD, TTS, streaming, and barge-in
* **Redis** — Semantic caching for repeated queries
* **Observability** — Langfuse traces for latency, tokens, cost, and tool calls
* **Production** — FastAPI streaming, Docker Compose, and evaluation-gated CI

## 🏗️ Architecture

```text
User (Text / Voice)
        ↓
     FastAPI
        ↓
    LangGraph
        ↓
 ┌──────┴────────┐
 │               │
RAG           MCP Hub
 │               │
pgvector      order-mcp
BM25          ticket-mcp
Reranker
 │
 └──────┬────────┘
        ↓
    Response
        │
   ┌────┴────┐
 Redis     Langfuse
```

## 🛠️ Tech Stack

**Python · LangGraph · FastAPI · PostgreSQL + pgvector · Redis · MCP SDK · LiveKit · Langfuse · Docker**


## 🔐 Safety

* Confidence-based human escalation
* MCP-based controlled tool execution
* API-key authentication
* Tool audit logging
* Automatic ticket creation after repeated voice failures

## 📌 Core Idea

**RAG + LangGraph + MCP + Voice + Observability + Caching** in one production-oriented customer-support system.

## Eval (50 golden tests, CI green)

| Metric | Score | Target |
| Tool Acc | 50/50 = 1.00 | 0.91 |
| Faithfulness | 42/50 = 0.84 | 0.92 |
| Unsafe Block | 7/7 = 1.00 | 1.00 |
| p95 text | 0.08s local | 1.5s prod |
| Cost | $0.002/query est | $0.002 |

- Demo: `http://localhost:8000/demo` (chat + mic + cached flag)
- CI: GitHub Actions `eval-gate` runs `backend.eval50` on every push
- Baseline: `docs/eval-baseline.md`