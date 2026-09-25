import os
from datetime import datetime

API_KEY = os.getenv("MCP_API_KEY", "vox-secret-123")
LOG_FILE = os.path.join(os.path.dirname(__file__), "audit.log")

def check_key(key: str) -> bool:
    return key == API_KEY

def audit(tool: str, args: dict, status: str):
    line = f"{datetime.utcnow().isoformat()} | {tool} | {args} | {status}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)