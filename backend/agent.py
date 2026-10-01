import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from backend.retriever import search as rag_search
from mcp_hub.order_server import get_order_status, get_policy
from mcp_hub.ticket_server import create_ticket
import re as _re

API_KEY = os.getenv("MCP_API_KEY", "vox-secret-123")

class State(TypedDict):
    query: str
    intent: str
    docs: List[dict]
    tool_result: dict
    answer: str
    confidence: float

def intent_node(state: State):
    q = state["query"].lower()
    if "approve" in q and "no question" in q:
            return {"intent": "unknown", "confidence": 0.4}
    if "create" in q and "ticket" in q:
        return {"intent": "ticket"}
    if any(w in q for w in ("cancel", "delete", "remove", "chargeback")) and ("my " in q or "order" in q or "#" in q):
        return {"intent": "unknown", "confidence": 0.4}
    if "order" in q or "track" in q or "#" in q:
        # Generic how-to questions about orders are policy questions, not tracking.
        # e.g. "how to return my order" -> policy; "where is my order 1001?" -> order.
        if any(w in q for w in ("how ", "how to", "kaise", "process", "way to")):
            return {"intent": "policy"}
        if "return" in q and not _re.search(r"#?\d{4}", q):
            return {"intent": "policy"}
        return {"intent": "order"}
    if "ticket" in q or "stuck" in q or "failed" in q:
        return {"intent": "ticket"}
    if any(w in q for w in ("refund", "ship", "deliver", "policy", "policies", "return", "cancellation", "cancel", "privacy", "account", "warranty", "payment", "terms", "price", "pric", "leave", "leaves", "notice", "period", "wfh", "maternity", "salary", "holiday", "holidays")):
        return {"intent": "policy"}
    return {"intent": "unknown", "confidence": 0.5}

def retriever_node(state: State):
    domain = "tickets" if state.get("intent") == "ticket" else "policy"
    docs = rag_search(state["query"], k=4, domain=domain)
    conf = 0.9 if docs and docs[0]["page"] != 0 else 0.6
    if state.get("intent") == "unknown":
        conf = min(conf, 0.5)
    return {"docs": docs, "confidence": conf}

def tool_router(state: State):
    intent = state.get("intent", "unknown")
    q = state["query"]
    if intent == "order":
        import re
        m = re.search(r"#?(\d{4})", q)
        if not m:
            return {"tool_result": {"ask": "order_id"}, "confidence": 0.6}
        oid = m.group(1)
        return {"tool_result": get_order_status(oid, API_KEY)}
    if intent == "ticket":
        if any(w in q.lower() for w in ("show", "search", "list", "history", "past", "my tickets")):
            from mcp_hub.ticket_server import search_past_tickets
            return {"tool_result": {"tickets": search_past_tickets(q, API_KEY)}}
        return {"tool_result": create_ticket("1003", q, API_KEY)}
    if intent == "policy":
        topic = "refund" if "refund" in q.lower() else "shipping"
        return {"tool_result": get_policy(topic, API_KEY)}
    return {"tool_result": {}}

def _plain(text: str) -> str:
    """Strip markdown so answers render as clean plain lines."""
    out = []
    for ln in (text or "").split("\n"):
        ln = ln.strip()
        ln = _re.sub(r"^#+\s*", "", ln)  # ### heading -> plain
        ln = _re.sub(r"^>\s*", "", ln)  # quote -> plain
        ln = ln.replace("**", "").replace("__", "").replace("`", "")
        ln = ln.replace("|", " ")  # tables -> spaces
        ln = _re.sub(r"\*(?=\S)", "", ln)  # stray * before word
        ln = _re.sub(r"(?<=\S)\*", "", ln)  # stray * after word
        ln = _re.sub(r"\s{2,}", " ", ln).strip()
        if ln in ("-", "*", "."):
            ln = ""
        elif ln.startswith(("- ", "* ")):
            ln = "• " + ln[2:].strip()
        elif ln.startswith("• "):
            ln = "• " + ln[2:].strip()
        out.append(ln)
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


_LLM = None

def _get_llm():
    global _LLM
    if _LLM is None:
        from langchain_groq import ChatGroq
        _LLM = ChatGroq(
            model=os.getenv("LLM_MODEL", "openai/gpt-oss-20b"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
        )
    return _LLM


_SYS = (
    "You are VoxServe, a customer support assistant. Answer ONLY from the numbered "
    "context below. Rules: plain text only (no markdown, no #, no *, no ` characters), "
    "maximum 4 short lines, then one blank line, then exactly one line like "
    "[SHIPPING_POLICY.md page 2] copied from the context. "
    "If the context does not contain the answer, reply exactly: "
    "Escalated to human agent, no docs found."
)

def _llm_answer(query: str, docs) -> str:
    ctx = "\n\n".join(
        f"[{d.get('source')} page {d.get('page')}]\n{(d.get('text') or '')[:700]}"
        for d in docs[:4]
    )
    resp = _get_llm().invoke([("system", _SYS), ("human", f"Context:\n{ctx}\n\nQuestion: {query}")])
    ans = _plain(resp.content if hasattr(resp, "content") else str(resp))
    if not _re.search(r"\[.+\.(?:md|pdf) page \d+\]", ans):
        top = docs[0]
        ans += f"\n\n[{top['source']} page {top['page']}]"
    return ans


def _docs_answer(docs) -> str:
    """Deterministic fallback: top chunk as short bullet lines."""
    top = docs[0]
    raw = (top['text'] or '').strip().replace('\r', '')
    lines = []
    for ln in raw.split('\n'):
        ln = _re.sub(r'^#+\s*', '', ln).replace('**', '').strip()
        if not ln:
            continue
        is_heading = bool(_re.match(r'^\d+\.\s+\S', ln)) and not _re.match(r'^\d+\.\d+', ln)
        segs = _re.split(r'(?<=[.;:])\s+', ln) if len(ln) > 110 else [ln]
        for s in segs:
            s = s.strip(' .-')
            if not s:
                continue
            if is_heading:
                lines.append(s)
                lines.append("")
            elif _re.match(r'^\d+\.\d+\s', s) or s.startswith(("-", "•")):
                lines.append(s)
            else:
                lines.append(f"• {s}")
        if len([x for x in lines if x]) >= 6:
            break
    lines = lines[:8] or [raw[:300]]
    body = '\n'.join(lines).strip()
    return f"{body}\n\n[{top['source']} page {top['page']}]"


def responder(state: State):
    if state.get("tool_result", {}).get("ask") == "order_id":
        return {"answer": "Please share your 4-digit order ID (e.g. 1001) so I can check the live status."}
    if state.get("confidence", 0.9) < 0.7:
        return {"answer": "Escalated to human agent due to low confidence."}
    if state.get("intent") == "order":
        r = state.get("tool_result", {})
        _m = _re.search(r"#?(\d{4})", state.get("query", ""))
        _oid = _m.group(1) if _m else ""
        return {"answer": f"Order {_oid} status: {r.get('status', 'unknown')}, tracking: {r.get('tracking', '-')}"}
    if state.get("intent") == "ticket":
        r = state.get("tool_result", {})
        if "tickets" in r:
            found = r["tickets"]
            if not found:
                return {"answer": "No past tickets found for that."}
            lines = "\n".join(f"• {t.get('ticket_id')}: {t.get('issue')}" for t in found[:5])
            return {"answer": _plain(f"Found {len(found)} past ticket(s):\n{lines}")}
        return {"answer": f"Ticket {r.get('ticket_id', '-')} created for your issue."}
    docs = state.get("docs", [])
    if not docs:
        return {"answer": "Escalated to human agent, no docs found."}
    try:
        answer = _llm_answer(state.get("query", ""), docs)
    except Exception:
        answer = _docs_answer(docs)  # LLM down -> same answer path still works
    return {"answer": _plain(answer)}

graph = StateGraph(State)
graph.add_node("intent_step", intent_node)
graph.add_node("retriever_step", retriever_node)
graph.add_node("router_step", tool_router)
graph.add_node("responder_step", responder)
graph.set_entry_point("intent_step")
graph.add_edge("intent_step", "retriever_step")
graph.add_edge("retriever_step", "router_step")
graph.add_edge("router_step", "responder_step")
graph.add_edge("responder_step", END)

app = graph.compile() 

if __name__ == "__main__":
    for q in [
        "Where is my order 1001?",
        "Refund for damaged product?",
        "Delivery stuck, create ticket",
        "xyz blabla unknown thing",
    ]:
        out = app.invoke({"query": q})
        print(f"Q: {q}\nA: {out['answer']}\n")