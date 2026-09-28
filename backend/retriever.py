import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from backend.chunk import splitter
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers import ContextualCompressionRetriever
from backend.ingest import load_with_pages, load_tickets_with_pages, load_md_with_pages



DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://vox:vox123@localhost:5434/voxserve"
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

_embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
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

_reranker_model = HuggingFaceCrossEncoder(
    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
)
_compressor = CrossEncoderReranker(model=_reranker_model, top_n=4)
final_policy = ContextualCompressionRetriever(
    base_compressor=_compressor,
    base_retriever=ensemble_policy
)
final_tickets = ContextualCompressionRetriever(
    base_compressor=_compressor,
    base_retriever=ensemble_tickets
)

def search(query, k=4, domain="policy"):
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