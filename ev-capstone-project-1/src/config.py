"""
Configuration module for Enterprise Operations Assistant.
Loads environment variables, initializes LLMs and Langfuse observability callbacks.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

# Langfuse Observability Settings
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"))

import logging
import socket
from urllib.parse import urlparse

# Service and Database Settings
MOCK_API_PORT = int(os.getenv("MOCK_API_PORT", "8000"))
MOCK_API_BASE_URL = f"http://127.0.0.1:{MOCK_API_PORT}"
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/operations.db")


def is_langfuse_reachable(host_url: Optional[str] = None) -> bool:
    """Checks whether the Langfuse server is reachable."""
    target_host = host_url or LANGFUSE_HOST
    try:
        parsed = urlparse(target_host)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except Exception:
        return False


def configure_observability():
    """
    Checks Langfuse connectivity.
    If unreachable, suppresses background connection retry logging to keep console clean.
    """
    if not is_langfuse_reachable():
        # Silence background retry logging in OpenTelemetry and urllib3
        for logger_name in [
            "opentelemetry",
            "opentelemetry.exporter.otlp",
            "opentelemetry.exporter.otlp.proto.http.trace_exporter",
            "urllib3",
            "urllib3.connectionpool",
        ]:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        return False
    return True


def get_llm(temperature: float = 0.0):
    """Returns an initialized ChatOpenAI instance."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        temperature=temperature,
        api_key=OPENAI_API_KEY,
    )


def get_langfuse_callback(
    trace_name: str = "Enterprise_Operations_Assistant",
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[list] = None,
):
    """
    Returns a configured Langfuse CallbackHandler for end-to-end tracing.
    If Langfuse is unavailable or keys are missing, returns None.
    """
    if not (LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY):
        return None

    try:
        try:
            import langfuse
            langfuse.get_client()
            from langfuse.langchain import CallbackHandler
            return CallbackHandler()
        except ImportError:
            from langfuse.callback import CallbackHandler
            return CallbackHandler(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
                trace_name=trace_name,
                session_id=session_id,
                user_id=user_id,
                tags=tags or ["capstone-operations-assistant"],
            )
    except Exception as e:
        print(f"[Warning] Could not initialize Langfuse CallbackHandler: {e}")
        return None
