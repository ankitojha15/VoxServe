import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
import redis
from backend.agent import app as agent_app
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
try:
    from langfuse import get_client
except Exception:
    get_client = None


app = FastAPI(title="VoxServe")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")
r = redis.from_url(REDIS_URL, decode_responses=True)

try:
    _lf = get_client() if get_client else None
    if _lf:
        _lf.auth_check()
except Exception:
    _lf = None

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

@app.get("/demo")
def demo():
    return FileResponse("frontend/index.html")

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

    if _lf:
        try:
            with _lf.start_as_current_observation(
                as_type="generation",
                name="chat-answer",
                model="openai/gpt-oss-20b",
                input=body.query,
            ) as gen:
                gen.update(output=data["answer"], metadata={"intent": data["intent"]})
            _lf.flush()
        except Exception:
            pass

    try:
        r.setex(key, 3600, json.dumps(data))
    except Exception:
        pass
    return data