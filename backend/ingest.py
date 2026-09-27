import os
import re
import glob
from langchain_huggingface import HuggingFaceEmbeddings
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

if __name__ == "__main__":
    all_docs = []
    for fname in ["refund-policy.txt", "shipping-help.txt"]:
        all_docs.extend(load_with_pages(f"data/raw/{fname}"))
    for fpath in glob.glob("data/raw/*.pdf"):
        all_docs.extend(load_pdf_with_pages(fpath))

    print(f"Total chunks: {len(all_docs)}")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    print(f"Embedding model: {EMBED_MODEL}")

    store = PGVector(
        embeddings=embeddings,
        collection_name="vox_docs",
        connection=DB_URL,
        use_jsonb=True,
    )
    try:
        store.delete_collection()
    except Exception:
        pass
    
    store = PGVector(
        embeddings=embeddings,
        collection_name="vox_docs",
        connection=DB_URL,
        use_jsonb=True,
    )

    store.add_documents(all_docs)
    print("Ingest done with source+page")