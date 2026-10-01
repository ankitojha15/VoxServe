import json
import math
import re as _re2
import redis
import os

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6380"), decode_responses=True)

# Bump on answer-format or intent-logic changes so deploys never serve stale cache.
CACHE_VERSION = "v2"

_HAS_ID = _re2.compile(r"\d{4}")

def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0

def sem_get(query, thresh=0.90):
    if _HAS_ID.search(query or ""):
        return None  # order IDs differ by 1 digit but mean different orders
    try:
        from backend.embeddings import get_embeddings
        qv = get_embeddings().embed_query(query)
        for key in r.scan_iter(f"sem:{CACHE_VERSION}:*"):
            d = json.loads(r.get(key))
            if _cos(qv, d["vec"]) >= thresh:
                data = d["data"]
                data["cached"] = "semantic"
                return data
    except Exception:
        pass
    return None

def sem_set(query, data, ttl=3600):
    if _HAS_ID.search(query or ""):
        return
    try:
        from backend.embeddings import get_embeddings
        qv = get_embeddings().embed_query(query)
        r.setex(f"sem:{CACHE_VERSION}:{query.strip().lower()}", ttl, json.dumps({"vec": qv, "data": data}))
    except Exception:
        pass