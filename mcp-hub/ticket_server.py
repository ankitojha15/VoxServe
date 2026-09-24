from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ticket-mcp")

TICKETS = []

@mcp.tool()
def create_ticket(order_id: str, issue: str) -> dict:
    """Create support ticket for order."""
    tid = f"T{len(TICKETS)+1:04d}"
    t = {"ticket_id": tid, "order_id": order_id, "issue": issue, "status": "open"}
    TICKETS.append(t)
    return t

@mcp.tool()
def search_past_tickets(query: str) -> list:
    """Search past tickets by keyword."""
    q = query.lower()
    return [t for t in TICKETS if q in t["issue"].lower() or q in t["order_id"]]

if __name__ == "__main__":
    print(create_ticket("1003", "delivery stuck for 48 hours"))
    print(search_past_tickets("stuck"))