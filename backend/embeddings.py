"""Embedding provider switch (LangChain native, no new pattern).

- local (default): HuggingFaceEmbeddings on torch. Dev speed, laptop.
- api: HF Inference API wrapper below. No torch needed at call time,
  tiny deploy image. Needs HF_TOKEN (free, no card).
- fallback: torch stack absent (slim image) -> API automatically.

Switch with env: EMBED_PROVIDER=local|api, EMBED_MODEL, HF_TOKEN.
"""

import os

from langchain_core.embeddings import Embeddings

PROVIDER = os.getenv("EMBED_PROVIDER", "local")
MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")


class _HFAPIEmbeddings(Embeddings):
    """LangChain-native wrapper over HF Inference API (no torch)."""

    def __init__(self, model, token):
        from huggingface_hub import InferenceClient

        self._client = InferenceClient(api_key=token)
        self._model = model

    def _flat(self, out):
        try:
            import numpy as _np

            arr = _np.asarray(out, dtype=float)
            return arr.reshape(-1).tolist() if arr.ndim > 1 else arr.tolist()
        except ImportError:
            return list(out[0]) if isinstance(out, list) and out else list(out)

    def embed_query(self, text):
        return self._flat(self._client.feature_extraction(text, model=self._model))

    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]


def get_embeddings():
    if PROVIDER != "api":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(model_name=MODEL)
        except ImportError:
            pass  # slim image: torch stack absent, fall through to API
    return _HFAPIEmbeddings(MODEL, os.getenv("HF_TOKEN"))


if __name__ == "__main__":
    emb = get_embeddings()
    vec = emb.embed_query("refund for damaged product")
    print(f"provider={PROVIDER} model={MODEL} dim={len(vec)}")
