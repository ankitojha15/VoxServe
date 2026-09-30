"""Embedding provider switch (LangChain native, no new pattern).

- local (default): HuggingFaceEmbeddings on torch. Dev speed, laptop.
- api: HuggingFaceEndpointEmbeddings via HF Inference API. No torch
  needed at call time, tiny deploy image. Needs HF_TOKEN (free, no card).

Switch with env: EMBED_PROVIDER=local|api, EMBED_MODEL, HF_TOKEN.
"""

import os

PROVIDER = os.getenv("EMBED_PROVIDER", "local")
MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")


def get_embeddings():
    if PROVIDER == "api":
        from langchain_huggingface import HuggingFaceEndpointEmbeddings

        return HuggingFaceEndpointEmbeddings(
            model=MODEL,
            huggingfacehub_api_token=os.getenv("HF_TOKEN"),
        )
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=MODEL)


if __name__ == "__main__":
    emb = get_embeddings()
    vec = emb.embed_query("refund for damaged product")
    print(f"provider={PROVIDER} model={MODEL} dim={len(vec)}")
