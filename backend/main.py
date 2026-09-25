import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
import redis
from backend.agent import app as agent_app

app = FastAPI(title="VoxServe")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")
r = redis.from_url(REDIS_URL, decode_responses=True)

class ChatIn(BaseModel):
    query: str

@app.get("/")
def root():
    return {"message": "VoxServe is running"}

@app.get("/health")
def health():
    try:
        r.ping()
        redis_status = "up"
    except Exception:
        redis_status = "down"
    return {"status": "ok", "redis": redis_status}

@app.post("/chat")
def chat(body: ChatIn):
    key = f"chat:{body.query.strip().lower()}"
    try:
        cached = r.get(key)
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return data
    except Exception:
        pass

    out = agent_app.invoke({"query": body.query})
    data = {
        "answer": out.get("answer", ""),
        "intent": out.get("intent", ""),
        "confidence": out.get("confidence", 0.0),
        "cached": False,
    }
    try:
        r.setex(key, 3600, json.dumps(data))
    except Exception:
        pass
    return data