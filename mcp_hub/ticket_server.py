from mcp.server.fastmcp import FastMCP
from mcp_hub.auth import check_key, audit
import json as _json
import os as os
import re

mcp = FastMCP("ticket-mcp")

TICKETS = []

_PAST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "past-tickets.json")
_RUNTIME = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "runtime-tickets.jsonl")
try:
    with open(_PAST) as _f:
        TICKETS.extend(_json.loads(line) for line in _f)
except FileNotFoundError:
    pass
try:
    with open(_RUNTIME) as _f:
        TICKETS.extend(_json.loads(line) for line in _f if line.strip())
except FileNotFoundError:
    pass

@mcp.tool()
def create_ticket(order_id: str, issue: str, api_key: str) -> dict:
    """Create support ticket for order."""
    if not check_key(api_key):
        audit("create_ticket", {"order_id": order_id}, "auth_fail")
        return {"error": "unauthorized"}
    tid = f"T{len(TICKETS)+1:04d}"
    t = {"ticket_id": tid, "order_id": order_id, "issue": issue, "status": "open"}
    TICKETS.append(t)
    try:
        with open(_RUNTIME, "a") as _f:
            _f.write(_json.dumps(t) + "\n")
    except OSError:
        pass
    audit("create_ticket", {"order_id": order_id}, "ok")
    return t

@mcp.tool()
def search_past_tickets(query: str, api_key: str) -> list:
    """Search past tickets by keyword."""
    if not check_key(api_key):
        audit("search_past_tickets", {"query": query}, "auth_fail")
        return [{"error": "unauthorized"}]
    q = query.lower()
    words = [w for w in re.findall(r"[a-z]+", q) if len(w) > 3 and w not in ("show", "past", "list", "search", "tickets", "ticket", "please")]
    if not words:
        result = TICKETS[-5:]
    else:
        result = [t for t in TICKETS if any(w in t["issue"].lower() or w in t["order_id"] for w in words)]
    audit("search_past_tickets", {"query": query}, "ok")
    return result

if __name__ == "__main__":
    print(create_ticket("1003", "delivery stuck for 48 hours", "vox-secret-123"))
    print(search_past_tickets("stuck", "vox-secret-123"))
    print(create_ticket("1001", "test", "wrong-key"))