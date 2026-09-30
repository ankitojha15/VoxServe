import os
from langchain_postgres import PGVector
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from backend.chunk import splitter
from langchain.retrievers import ContextualCompressionRetriever
from backend.ingest import load_with_pages, load_tickets_with_pages, load_md_with_pages



DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://vox:vox123@localhost:5434/voxserve"
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
RERANK_PROVIDER = os.getenv("RERANK_PROVIDER", "cross")

# ---- lazy singletons: import-time pe torch/model load nahi hota ----
# Isliye server turant port kholta hai (Render health check) aur RAM 512MB me rehta hai.
_cache = {}


def _emb():
    if "emb" not in _cache:
        from backend.embeddings import get_embeddings

        _cache["emb"] = get_embeddings()
    return _cache["emb"]


def _store(collection):
    key = f"store:{collection}"
    if key not in _cache:
        _cache[key] = PGVector(
            embeddings=_emb(),
            collection_name=collection,
            connection=DB_URL,
            use_jsonb=True,
        )
    return _cache[key]


def _dense(domain):
    key = f"dense:{domain}"
    if key not in _cache:
        _cache[key] = _store(f"vox_{domain}").as_retriever(search_kwargs={"k": 10})
    return _cache[key]


def _bm25_docs_policy():
    import glob as _glob
    docs = []
    for fpath in sorted(_glob.glob("data/raw/*.md")):
        docs.extend(load_md_with_pages(fpath))
    return docs


def _bm25_docs_tickets():
    return load_tickets_with_pages()


def _bm25(domain):
    key = f"bm25:{domain}"
    if key not in _cache:
        docs = _bm25_docs_tickets() if domain == "tickets" else _bm25_docs_policy()
        r = BM25Retriever.from_documents(docs)
        r.k = 10
        _cache[key] = r
    return _cache[key]


def _ensemble(domain):
    key = f"ensemble:{domain}"
    if key not in _cache:
        _cache[key] = EnsembleRetriever(
            retrievers=[_dense(domain), _bm25(domain)],
            weights=[0.7, 0.3],
        )
    return _cache[key]


def _compressor():
    if "comp" not in _cache:
        if RERANK_PROVIDER == "rrf":
            _cache["comp"] = None
        else:
            from langchain.retrievers.document_compressors import CrossEncoderReranker
            from langchain_community.cross_encoders import HuggingFaceCrossEncoder

            _cache["comp"] = CrossEncoderReranker(
                model=HuggingFaceCrossEncoder(
                    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
                ),
                top_n=4,
            )
    return _cache["comp"]


def _final(domain):
    key = f"final:{domain}"
    if key not in _cache:
        _cache[key] = ContextualCompressionRetriever(
            base_compressor=_compressor(),
            base_retriever=_ensemble(domain),
        )
    return _cache[key]


def _rrf_fuse(query, dense_r, bm25_r, k=20, top_n=4, const=60):
    """Pure-python Reciprocal Rank Fusion over two retrievers (no torch, no API)."""
    scores = {}
    order = {}

    def _key(d):
        return (d.metadata.get("source", ""), d.metadata.get("page", 0), d.page_content[:200])

    for rank, d in enumerate(dense_r.invoke(query)[:k] if hasattr(dense_r, "invoke") else [], start=1):
        kk = _key(d)
        scores[kk] = scores.get(kk, 0.0) + 1.0 / (const + rank)
        order.setdefault(kk, d)
    for rank, d in enumerate(bm25_r.invoke(query)[:k] if hasattr(bm25_r, "invoke") else [], start=1):
        kk = _key(d)
        scores[kk] = scores.get(kk, 0.0) + 1.0 / (const + rank)
        order.setdefault(kk, d)
    ranked = sorted(scores, key=scores.get, reverse=True)
    return [order[kk] for kk in ranked[:top_n]]


def search(query, k=4, domain="policy"):
    if RERANK_PROVIDER == "rrf":
        docs = _rrf_fuse(query, _dense(domain), _bm25(domain), k=20, top_n=k)
    else:
        docs = _final(domain).invoke(query)
    results = []
    for d in docs[:k]:
        results.append({
            "text": d.page_content,
            "source": d.metadata.get("source", "unknown"),
            "page": d.metadata.get("page", 0)
        })
    return results

if __name__ == "__main__":
    q = "refund for damaged product in how many days?"
    hits = search(q)
    print(f"Found: {len(hits)}")
    for h in hits:
        print(f"[{h['source']} page {h['page']}] {h['text'][:150]}")
