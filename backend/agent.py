import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from backend.retriever import search as rag_search
from mcp_hub.order_server import get_order_status, get_policy
from mcp_hub.ticket_server import create_ticket

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
    if "order" in q or "track" in q or "#" in q:
        return {"intent": "order"}
    if "ticket" in q or "stuck" in q or "failed" in q:
        return {"intent": "ticket"}
    if "refund" in q or "ship" in q or "deliver" in q or "policy" in q:
        return {"intent": "policy"}
    return {"intent": "unknown", "confidence": 0.5}


def retriever_node(state: State):
    docs = rag_search(state["query"], k=4)
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
        oid = m.group(1) if m else "1001"
        return {"tool_result": get_order_status(oid, API_KEY)}
    if intent == "ticket":
        return {"tool_result": create_ticket("1003", q, API_KEY)}
    if intent == "policy":
        topic = "refund" if "refund" in q.lower() else "shipping"
        return {"tool_result": get_policy(topic, API_KEY)}
    return {"tool_result": {}}

def responder(state: State):
    if state.get("confidence", 0.9) < 0.7:
        return {"answer": "Escalated to human agent due to low confidence."}
    if state.get("intent") == "order":
        r = state.get("tool_result", {})
        return {"answer": f"Order status: {r.get('status', 'unknown')}, tracking: {r.get('tracking', '-')}"}
    if state.get("intent") == "ticket":
        r = state.get("tool_result", {})
        return {"answer": f"Ticket {r.get('ticket_id', '-')} created for your issue."}
    docs = state.get("docs", [])
    if not docs:
        return {"answer": "Escalated to human agent, no docs found."}
    top = docs[0]
    return {"answer": f"{top['text'][:300]} [{top['source']} page {top['page']}]"}

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