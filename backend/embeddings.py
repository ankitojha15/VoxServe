"""Embedding provider switch — the ONE place that defines embed config.

- fastembed (default): local ONNX model. Free, no API key, no torch.
- cohere: Cohere Embeddings API. Needs COHERE_API_KEY. No torch.

Switch with env: EMBED_PROVIDER=fastembed|cohere, EMBED_MODEL.
All other files import PROVIDER/MODEL from here — no copy-paste defaults.
"""

import os

from langchain_core.embeddings import Embeddings

PROVIDER = os.getenv("EMBED_PROVIDER", "fastembed")
MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")


class _FastEmbedEmbeddings(Embeddings):
    """Local ONNX embeddings via fastembed. No torch, no API key."""

    def __init__(self, model):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model)

    def embed_query(self, text):
        return next(self._model.embed([text])).tolist()

    def embed_documents(self, texts):
        return [v.tolist() for v in self._model.embed(texts)]


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
    if PROVIDER == "fastembed":
        return _FastEmbedEmbeddings(MODEL)
    if PROVIDER == "cohere":
        return _CohereEmbeddings(MODEL, os.getenv("COHERE_API_KEY"))
    raise RuntimeError(
        f"Unknown EMBED_PROVIDER '{PROVIDER}'. Use 'fastembed' (default, free, no key) or 'cohere'."
    )


if __name__ == "__main__":
    emb = get_embeddings()
    vec = emb.embed_query("refund for damaged product")
    print(f"provider={PROVIDER} model={MODEL} dim={len(vec)}")
