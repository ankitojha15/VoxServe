from mcp.server.fastmcp import FastMCP
from mcp_hub.auth import check_key, audit

mcp = FastMCP("ticket-mcp")

TICKETS = []

@mcp.tool()
def create_ticket(order_id: str, issue: str, api_key: str) -> dict:
    """Create support ticket for order."""
    if not check_key(api_key):
        audit("create_ticket", {"order_id": order_id}, "auth_fail")
        return {"error": "unauthorized"}
    tid = f"T{len(TICKETS)+1:04d}"
    t = {"ticket_id": tid, "order_id": order_id, "issue": issue, "status": "open"}
    TICKETS.append(t)
    audit("create_ticket", {"order_id": order_id}, "ok")
    return t

@mcp.tool()
def search_past_tickets(query: str, api_key: str) -> list:
    """Search past tickets by keyword."""
    if not check_key(api_key):
        audit("search_past_tickets", {"query": query}, "auth_fail")
        return [{"error": "unauthorized"}]
    q = query.lower()
    result = [t for t in TICKETS if q in t["issue"].lower() or q in t["order_id"]]
    audit("search_past_tickets", {"query": query}, "ok")
    return result

if __name__ == "__main__":
    print(create_ticket("1003", "delivery stuck for 48 hours", "vox-secret-123"))
    print(search_past_tickets("stuck", "vox-secret-123"))
    print(create_ticket("1001", "test", "wrong-key"))