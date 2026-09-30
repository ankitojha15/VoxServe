"""HuggingFace Spaces entrypoint (free, no Docker, no card).

The Space runs `python app.py`; we launch the same FastAPI app the
Dockerfile runs locally, on the Space-provided $PORT. Full console
(/demo), API, and eval pipeline stay identical - only the host changes.
Heavy data lives in Supabase + Upstash (see Space secrets).
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7860")),
    )
