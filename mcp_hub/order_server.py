from mcp.server.fastmcp import FastMCP
from mcp_hub.auth import check_key, audit

mcp = FastMCP("order-mcp")

ORDERS = {
    "1001": {"status": "shipped", "tracking": "TRK1001"},
    "1002": {"status": "delivered", "tracking": "TRK1002"},
    "1003": {"status": "stuck", "tracking": "TRK1003"},
}

@mcp.tool()
def get_order_status(order_id: str, api_key: str) -> dict:
    """Get live order status by order ID."""
    if not check_key(api_key):
        audit("get_order_status", {"order_id": order_id}, "auth_fail")
        return {"error": "unauthorized"}
    result = ORDERS.get(order_id, {"status": "not_found"})
    audit("get_order_status", {"order_id": order_id}, "ok")
    return result

@mcp.tool()
def get_policy(topic: str, api_key: str) -> dict:
    """Get policy by topic: refund or shipping."""
    if not check_key(api_key):
        audit("get_policy", {"topic": topic}, "auth_fail")
        return {"error": "unauthorized"}
    topic = topic.lower()
    if "refund" in topic:
        result = {"topic": "refund", "text": open("data/raw/refund-policy.txt").read()[:1000]}
    elif "ship" in topic:
        result = {"topic": "shipping", "text": open("data/raw/shipping-help.txt").read()[:1000]}
    else:
        result = {"topic": topic, "text": "policy not found"}
    audit("get_policy", {"topic": topic}, "ok")
    return result

if __name__ == "__main__":
    print(get_order_status("1001", "vox-secret-123"))
    print(get_order_status("1001", "wrong-key"))
    print(get_policy("refund", "vox-secret-123"))