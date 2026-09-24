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
from backend.ingest import load_with_pages


DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://vox:vox123@localhost:5434/voxserve"
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

_embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
_store = PGVector(
    embeddings=_embeddings,
    collection_name="vox_docs",
    connection=DB_URL,
    use_jsonb=True,
)

dense = _store.as_retriever(search_kwargs={"k": 10})

# BM25 ke liye same chunks memory me
def _bm25_docs():
    docs = []
    for fname in ["refund-policy.txt", "shipping-help.txt"]:
        docs.extend(load_with_pages(f"data/raw/{fname}"))
    return docs

bm25 = BM25Retriever.from_documents(_bm25_docs())
bm25.k = 10

ensemble = EnsembleRetriever(
    retrievers=[dense, bm25],
    weights=[0.7, 0.3]
)

_reranker_model = HuggingFaceCrossEncoder(
    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
)
_compressor = CrossEncoderReranker(model=_reranker_model, top_n=4)
final_retriever = ContextualCompressionRetriever(
    base_compressor=_compressor,
    base_retriever=ensemble
)

def search(query, k=4):
    docs = final_retriever.invoke(query)
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