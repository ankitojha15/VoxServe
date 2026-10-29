"""Embedding config — the ONE place that defines embed setup.

fastembed: local ONNX model. Free, no API key, no torch.
Env: EMBED_PROVIDER=fastembed (default), EMBED_MODEL=BAAI/bge-small-en-v1.5.
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


def get_embeddings():
    if PROVIDER != "fastembed":
        raise RuntimeError(
            f"Unknown EMBED_PROVIDER '{PROVIDER}'. Only 'fastembed' is supported (free, local)."
        )
    return _FastEmbedEmbeddings(MODEL)


if __name__ == "__main__":
    emb = get_embeddings()
    vec = emb.embed_query("refund for damaged product")
    print(f"provider={PROVIDER} model={MODEL} dim={len(vec)}")
