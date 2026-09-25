import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_DIR = Path(__file__).resolve().parent.parent

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", None)
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Observability Configuration (Langfuse / LangSmith)
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")

# Default paths
DEFAULT_CLONE_DIR = Path(os.getenv("CLONE_DIR", str(WORKSPACE_DIR / "workspace_clones")))
DEFAULT_CLONE_DIR.mkdir(parents=True, exist_ok=True)
