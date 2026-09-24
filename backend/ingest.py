import os
import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from backend.chunk import splitter

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

if __name__ == "__main__":
    all_docs = []
    for fname in ["refund-policy.txt", "shipping-help.txt"]:
        all_docs.extend(load_with_pages(f"data/raw/{fname}"))

    print(f"Total chunks: {len(all_docs)}")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    print(f"Embedding model: {EMBED_MODEL}")

    store = PGVector(
        embeddings=embeddings,
        collection_name="vox_docs",
        connection=DB_URL,
        use_jsonb=True,
    )

    store.add_documents(all_docs)
    print("Ingest done with source+page")