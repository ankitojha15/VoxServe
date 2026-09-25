import os
from backend.agent import app as agent_app
from mcp_hub.ticket_server import create_ticket

API_KEY = os.getenv("MCP_API_KEY", "vox-secret-123")
miss = 0

def handle_text(text: str):
    global miss
    out = agent_app.invoke({"query": text})
    conf = out.get("confidence", 0.9)
    if conf < 0.7 or "Escalated" in out.get("answer", ""):
        miss += 1
        print(f"Miss {miss}/2: {out['answer']}")
        if miss >= 2:
            t = create_ticket("VOICE-1", f"voice fail 2 times, last: {text}", API_KEY)
            miss = 0
            return f"Auto-ticket {t.get('ticket_id')} created for human."
        return out["answer"]
    miss = 0
    return out["answer"]

if __name__ == "__main__":
    for t in [
        "Where is my order 1001?",
        "xyz blabla",
        "abc nonsense talk",
        "Refund for damaged product?",
    ]:
        print(f"IN: {t}\nOUT: {handle_text(t)}\n")