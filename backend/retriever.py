import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector

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

_retriever = _store.as_retriever(search_kwargs={"k": 4})

def search(query, k=4):
    _retriever.search_kwargs = {"k": k}
    docs = _retriever.invoke(query)
    results = []
    for d in docs:
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