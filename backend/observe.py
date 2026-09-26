"""Langfuse v4 tracing helpers (OpenTelemetry-based SDK).

All helpers are exception-safe: with no configured client they are no-ops,
so the API never breaks when keys are missing. Never import heavy modules
here - this file must stay importable without DB, Redis, or network.
"""

import os

APP_VERSION = "1.0"
APP_ENV = os.getenv("APP_ENV", "dev")


def get_trace_client():
    """Return an authenticated v4 client, or None when unavailable."""
    try:
        from langfuse import get_client
    except Exception:
        return None
    try:
        client = get_client()
        client.auth_check()
        return client
    except Exception:
        return None


def trace_chat(client, query, answer, intent):
    """Record one /chat turn: root span carries overall I/O, nested
    generation carries the model answer. Session/user IDs are intentionally
    absent - the demo has no user concept (see jev-plan candidacy note)."""
    if client is None:
        return
    try:
        from langfuse import propagate_attributes

        with propagate_attributes(
            trace_name="chat",
            environment=APP_ENV,
            version=APP_VERSION,
            metadata={"intent": intent},
        ):
            with client.start_as_current_observation(
                as_type="span", name="chat", input=query
            ) as span:
                with client.start_as_current_observation(
                    as_type="generation",
                    name="chat-answer",
                    model="openai/gpt-oss-20b",
                    input=query,
                ) as gen:
                    gen.update(output=answer, metadata={"intent": intent})
                span.update(output=answer)
        client.flush()
    except Exception:
        pass
