import json
import math
import redis
import os

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6380"), decode_responses=True)

def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0

def sem_get(query, thresh=0.90):
    try:
        from backend.retriever import _embeddings
        qv = _embeddings.embed_query(query)
        for key in r.scan_iter("sem:*"):
            d = json.loads(r.get(key))
            if _cos(qv, d["vec"]) >= thresh:
                data = d["data"]
                data["cached"] = "semantic"
                return data
    except Exception:
        pass
    return None

def sem_set(query, data, ttl=3600):
    try:
        from backend.retriever import _embeddings
        qv = _embeddings.embed_query(query)
        r.setex(f"sem:{query.strip().lower()}", ttl, json.dumps({"vec": qv, "data": data}))
    except Exception:
        pass