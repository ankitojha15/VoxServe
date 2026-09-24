from mcp.server.fastmcp import FastMCP

mcp = FastMCP("order-mcp")

ORDERS = {
    "1001": {"status": "shipped", "tracking": "TRK1001"},
    "1002": {"status": "delivered", "tracking": "TRK1002"},
    "1003": {"status": "stuck", "tracking": "TRK1003"},
}

@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """Get live order status by order ID."""
    return ORDERS.get(order_id, {"status": "not_found"})

@mcp.tool()
def get_policy(topic: str) -> dict:
    """Get policy by topic: refund or shipping."""
    topic = topic.lower()
    if "refund" in topic:
        return {"topic": "refund", "text": open("data/raw/refund-policy.txt").read()[:1000]}
    if "ship" in topic:
        return {"topic": "shipping", "text": open("data/raw/shipping-help.txt").read()[:1000]}
    return {"topic": topic, "text": "policy not found"}

if __name__ == "__main__":
    print(get_order_status("1001"))
    print(get_policy("refund"))