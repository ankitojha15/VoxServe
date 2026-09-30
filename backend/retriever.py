import os
from backend.embeddings import get_embeddings, MODEL as EMBED_MODEL
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

_embeddings = get_embeddings()
def _make_store(collection):
    return PGVector(
        embeddings=_embeddings,
        collection_name=collection,
        connection=DB_URL,
        use_jsonb=True,
    )

_store_policy = _make_store("vox_policy")
_store_tickets = _make_store("vox_tickets")

dense_policy = _store_policy.as_retriever(search_kwargs={"k": 10})
dense_tickets = _store_tickets.as_retriever(search_kwargs={"k": 10})

# BM25 ke liye same chunks memory me
def _bm25_docs_policy():
    import glob as _glob
    docs = []
    for fpath in sorted(_glob.glob("data/raw/*.md")):
        docs.extend(load_md_with_pages(fpath))
    return docs

def _bm25_docs_tickets():
    return load_tickets_with_pages()

bm25_policy = BM25Retriever.from_documents(_bm25_docs_policy())
bm25_policy.k = 10
bm25_tickets = BM25Retriever.from_documents(_bm25_docs_tickets())
bm25_tickets.k = 10

ensemble_policy = EnsembleRetriever(
    retrievers=[dense_policy, bm25_policy],
    weights=[0.7, 0.3]
)
ensemble_tickets = EnsembleRetriever(
    retrievers=[dense_tickets, bm25_tickets],
    weights=[0.7, 0.3]
)

RERANK_PROVIDER = os.getenv("RERANK_PROVIDER", "cross")


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


def _get_dense_bm25(domain):
    if domain == "tickets":
        return dense_tickets, bm25_tickets
    return dense_policy, bm25_policy


if RERANK_PROVIDER == "rrf":
    _compressor = None
else:
    from langchain.retrievers.document_compressors import CrossEncoderReranker
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder

    _reranker_model = HuggingFaceCrossEncoder(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    _compressor = CrossEncoderReranker(model=_reranker_model, top_n=4)
if _compressor is None:
    final_policy = None
    final_tickets = None
else:
    final_policy = ContextualCompressionRetriever(
        base_compressor=_compressor,
        base_retriever=ensemble_policy
    )
    final_tickets = ContextualCompressionRetriever(
        base_compressor=_compressor,
        base_retriever=ensemble_tickets
    )

def search(query, k=4, domain="policy"):
    if RERANK_PROVIDER == "rrf":
        dense_r, bm25_r = _get_dense_bm25(domain)
        docs = _rrf_fuse(query, dense_r, bm25_r, k=20, top_n=k)
    else:
        retriever = final_tickets if domain == "tickets" else final_policy
        docs = retriever.invoke(query)
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