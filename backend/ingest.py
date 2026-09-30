import os
import re
import glob
from backend.embeddings import get_embeddings, MODEL as EMBED_MODEL
from langchain_postgres import PGVector
from langchain_core.documents import Document
from backend.chunk import splitter
from langchain_community.document_loaders import PyPDFLoader

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://vox:vox123@localhost:5434/voxserve"
)

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

def load_with_pages(path):
    text = open(path).read()
    parts = re.split(r"\[Page (\d+)\]", text)
    docs = []
    source = os.path.basename(path)
    for i in range(1, len(parts), 2):
        page = int(parts[i])
        content = parts[i+1] if i+1 < len(parts) else ""
        for chunk in splitter.split_text(content):
            docs.append(Document(
                page_content=chunk,
                metadata={"source": source, "page": page}
            ))
    return docs

def load_md_with_pages(path):
    import re as _re2
    text = open(path).read()
    parts = _re2.split(r"(?m)^##\s+", text)
    docs = []
    source = os.path.basename(path)
    if len(parts) <= 1:
        for chunk in splitter.split_text(text):
            docs.append(Document(page_content=chunk, metadata={"source": source, "page": 1}))
        return docs
    for i, part in enumerate(parts[1:], start=1):
        for chunk in splitter.split_text(part):
            docs.append(Document(page_content=chunk, metadata={"source": source, "page": i}))
    return docs

def load_pdf_with_pages(path):
    raw = PyPDFLoader(path).load()
    docs = []
    source = os.path.basename(path)
    for d in raw:
        for chunk in splitter.split_text(d.page_content):
            docs.append(Document(
                page_content=chunk,
                metadata={"source": source, "page": d.metadata.get("page", 0) + 1}
            ))
    return docs

def load_url_with_pages(url):
    from langchain_community.document_loaders import WebBaseLoader
    raw = WebBaseLoader(url).load()
    docs = []
    for d in raw:
        for chunk in splitter.split_text(d.page_content):
            docs.append(Document(
                page_content=chunk,
                metadata={"source": url, "page": 1}
            ))
    return docs

def load_tickets_with_pages(path="data/past-tickets.json"):
    import json
    docs = []
    try:
        fp = open(path)
    except FileNotFoundError:
        return docs
    for line in fp:
        t = json.loads(line)
        text = f"Order {t['order_id']}: {t['issue']}. Resolution: {t['resolution']}"
        for chunk in splitter.split_text(text):
            docs.append(Document(
                page_content=chunk,
                metadata={"source": "past-tickets.json", "page": 1}
            ))
    return docs

URLS = [
        # "https://example.com/shipping-help",
    ]
if __name__ == "__main__":
    embeddings = get_embeddings()
    print(f"Embedding model: {EMBED_MODEL}")

    policy_docs = []
    for fpath in sorted(glob.glob("data/raw/*.md")):
        policy_docs.extend(load_md_with_pages(fpath))
    for fpath in glob.glob("data/raw/*.pdf"):
        policy_docs.extend(load_pdf_with_pages(fpath))
    for url in URLS:
        policy_docs.extend(load_url_with_pages(url))

    ticket_docs = load_tickets_with_pages()

    print(f"Policy chunks: {len(policy_docs)}, Ticket chunks: {len(ticket_docs)}")

    for name, docs in [("vox_policy", policy_docs), ("vox_tickets", ticket_docs)]:
        store = PGVector(
            embeddings=embeddings,
            collection_name=name,
            connection=DB_URL,
            use_jsonb=True,
        )
        try:
            store.delete_collection()
        except Exception:
            pass
        store = PGVector(
            embeddings=embeddings,
            collection_name=name,
            connection=DB_URL,
            use_jsonb=True,
        )
        if docs:
            store.add_documents(docs)
    print("Ingest done: 2 collections")