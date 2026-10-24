"""Embedding provider switch.

- cohere: Cohere Embeddings API. Free tier. No torch.
- local: HuggingFaceEmbeddings on torch. Dev speed, laptop.

Switch with env: EMBED_PROVIDER=cohere|local, EMBED_MODEL, COHERE_API_KEY.
"""

import os

from langchain_core.embeddings import Embeddings

PROVIDER = os.getenv("EMBED_PROVIDER", "local")
MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")


class _CohereEmbeddings(Embeddings):
    """LangChain-native wrapper over Cohere Embeddings API (no torch)."""

    def __init__(self, model, api_key):
        from langchain_cohere import CohereEmbeddings

        self._client = CohereEmbeddings(model=model, cohere_api_key=api_key)

    def embed_query(self, text):
        return self._client.embed_query(text)

    def embed_documents(self, texts):
        return self._client.embed_documents(texts)


def get_embeddings():
    if PROVIDER == "cohere":
        return _CohereEmbeddings(MODEL, os.getenv("COHERE_API_KEY"))

    # default: local HF embeddings (dev/laptop only)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=MODEL)
    except ImportError:
        raise RuntimeError(
            "EMBED_PROVIDER is not 'cohere' and torch stack is missing. "
            "Set EMBED_PROVIDER=cohere and COHERE_API_KEY for Render."
        )



if __name__ == "__main__":
    emb = get_embeddings()
    vec = emb.embed_query("refund for damaged product")
    print(f"provider={PROVIDER} model={MODEL} dim={len(vec)}")
