import os
import json
from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel
import redis
from backend.agent import app as agent_app
from backend.observe import get_trace_client, trace_chat
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
try:
    from langfuse import get_client  # noqa: F401 (v4 entrypoint lives in observe.py)
except Exception:
    get_client = None
    

load_dotenv(override=True)

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
    _lf = get_trace_client()
    print(f"Langfuse: {'enabled on ' + os.getenv('LANGFUSE_HOST', '?') if _lf else 'DISABLED (no valid key)'}")
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

    trace_chat(_lf, body.query, data["answer"], data["intent"])

    try:
        r.setex(key, 3600, json.dumps(data))
    except Exception:
        pass
    return data


@app.post("/chat/stream")
def chat_stream(body: ChatIn):
    out = agent_app.invoke({"query": body.query})
    ans = out.get("answer", "")
    def gen():
        for i in range(0, len(ans), 50):
            yield f"data: {ans[i:i+50]}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")