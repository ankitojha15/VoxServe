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
from fastapi import UploadFile, File
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


@app.middleware("http")
async def no_store_html(request, call_next):
    resp = await call_next(request)
    if request.url.path in ("/", "/demo"):
        resp.headers["Cache-Control"] = "no-store"
    return resp

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
    return FileResponse("frontend/index.html")

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

class TokenIn(BaseModel):
    room: str = "voice-room-1"
    name: str = "user1"

@app.post("/voice/token")
def voice_token(body: TokenIn):
    from backend.voice_live import make_token
    return {"token": make_token(body.room, body.name), "url": os.getenv("LIVEKIT_URL")}


@app.post("/ingest/pdf")
def ingest_pdf(file: UploadFile = File(...)):
    path = f"data/raw/{file.filename}"
    with open(path, "wb") as f:
        f.write(file.file.read())
    from backend.ingest import load_pdf_with_pages
    from backend.embeddings import get_embeddings
    from langchain_postgres import PGVector
    docs = load_pdf_with_pages(path)
    emb = get_embeddings()
    store = PGVector(embeddings=emb, collection_name="vox_policy", connection=os.getenv("DATABASE_URL", "postgresql+psycopg://vox:vox123@localhost:5434/voxserve"), use_jsonb=True)
    if docs:
        store.add_documents(docs)
    return {"file": file.filename, "chunks": len(docs)}

@app.get("/sources")
def sources():
    import glob, os
    files = []
    for f in sorted(glob.glob("data/raw/*")):
        try:
            files.append({"name": f, "kb": round(os.path.getsize(f) / 1024, 1)})
        except OSError:
            pass
    return {"policy_files": files, "urls": []}

@app.get("/admin/ingest")
def admin_ingest(key: str = ""):
    if key != os.getenv("MCP_API_KEY", "vox-secret-123"):
        return {"error": "unauthorized"}
    from backend.ingest import (
        load_md_with_pages, load_pdf_with_pages,
        load_tickets_with_pages, DB_URL,
    )
    import glob as _glob
    from backend.embeddings import get_embeddings
    from langchain_postgres import PGVector
    docs = []
    for fp in sorted(_glob.glob("data/raw/*.md")):
        docs.extend(load_md_with_pages(fp))
    for fp in _glob.glob("data/raw/*.pdf"):
        docs.extend(load_pdf_with_pages(fp))
    emb = get_embeddings()
    store = PGVector(embeddings=emb, collection_name="vox_policy", connection=DB_URL, use_jsonb=True)
    try:
        store.delete_collection()
    except Exception:
        pass
    store = PGVector(embeddings=emb, collection_name="vox_policy", connection=DB_URL, use_jsonb=True)
    if docs:
        store.add_documents(docs)
    return {"policy_chunks": len(docs)}

@app.delete("/ingest/file")
def delete_file(name: str):
    import glob
    base = os.path.basename(name)
    path = os.path.join("data", "raw", base)
    if not os.path.isfile(path):
        return {"deleted": False}
    os.remove(path)
    from backend.ingest import load_md_with_pages, load_pdf_with_pages, DB_URL
    import glob as _glob
    from backend.embeddings import get_embeddings
    from langchain_postgres import PGVector
    docs = []
    for fp in sorted(_glob.glob("data/raw/*.md")):
        docs.extend(load_md_with_pages(fp))
    for fp in _glob.glob("data/raw/*.pdf"):
        docs.extend(load_pdf_with_pages(fp))
    emb = get_embeddings()
    store = PGVector(embeddings=emb, collection_name="vox_policy", connection=DB_URL, use_jsonb=True)
    try:
        store.delete_collection()
    except Exception:
        pass
    store = PGVector(embeddings=emb, collection_name="vox_policy", connection=DB_URL, use_jsonb=True)
    if docs:
        store.add_documents(docs)
    return {"deleted": True, "file": base, "policy_chunks": len(docs)}

@app.post("/chat")
def chat(body: ChatIn):
    import re as _re2
    ql = body.query.strip().lower()
    is_write = "ticket" in ql and any(w in ql for w in ("create", "new", "book", "file"))
    key = f"chat:{ql}"
    if not is_write:
        try:
            cached = r.get(key)
            if cached:
                data = json.loads(cached)
                data["cached"] = True
                return data
        except Exception:
            pass

        from backend.sem_cache import sem_get
        sem_hit = sem_get(body.query)
        if sem_hit:
            return sem_hit
    
    out = agent_app.invoke({"query": body.query})
    data = {
        "answer": out.get("answer", ""),
        "intent": out.get("intent", ""),
        "confidence": out.get("confidence", 0.0),
        "cached": False,
        "need_id": out.get("tool_result", {}).get("ask") == "order_id",
    }

    trace_chat(_lf, body.query, data["answer"], data["intent"])

    if not is_write:
        try:
            r.setex(key, 3600, json.dumps(data))
            from backend.sem_cache import sem_set
            sem_set(body.query, {k: v for k, v in data.items() if k != "cached"})
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