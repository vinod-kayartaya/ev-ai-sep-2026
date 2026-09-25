# Local Langfuse Setup

A lightweight, bare-minimum Docker Compose setup for running [Langfuse](https://langfuse.com) locally to monitor, trace, and evaluate LLM activities.

---

## Architecture

This setup runs the official Langfuse stack:
- **`langfuse-web`**: Web dashboard and ingestion API (`http://localhost:3000`).
- **`langfuse-worker`**: Background worker for async task processing and ingestion queues.
- **`postgres`**: Relational database for accounts, projects, and metadata.
- **`clickhouse`**: High-performance analytical database for traces, observations, and telemetry.
- **`minio`**: Lightweight S3-compatible object storage for event batches and media.
- **`redis`**: Cache and message queue for BullMQ background jobs.

---

## Quick Start

### 1. Start the stack
From inside the `langfuse` directory:

```bash
cd langfuse
docker compose up -d
```

Docker will download the images and start all services. On the first run, database migrations will run automatically.

### 2. Verify containers are healthy
Check the status of the containers:

```bash
docker compose ps
```

Wait a few moments until all services show as `healthy` or `running`.

### 3. Open the Dashboard
Navigate to [http://localhost:3000](http://localhost:3000) in your browser.

---

## Default Credentials & API Keys

By default, `.env` is configured with **Headless Initialization** so you don't need to manually configure projects or keys on first launch:

| Field | Default Value | Notes |
| :--- | :--- | :--- |
| **Email** | `admin@langfuse.local` | Sign-in email |
| **Password** | `adminpassword123` | Sign-in password |
| **Organization** | `Local Organization` | ID: `local-org` |
| **Project** | `Local Project` | ID: `local-project` |
| **Public Key** | `pk-lf-local-demo-1234567890` | For client SDKs |
| **Secret Key** | `sk-lf-local-demo-1234567890` | For backend SDKs |
| **Host** | `http://localhost:3000` | Local endpoint |

> **Note:** If you prefer to manually register via the web UI, simply comment out the `LANGFUSE_INIT_*` variables in `.env` before running `docker compose up -d`.

---

## Monitoring LLM Activities

### Option A: Quick Test Script

A test script is included in this directory.

1. Install the Langfuse Python SDK:
   ```bash
   pip install langfuse
   ```

2. Run the sample trace:
   ```bash
   python example_trace.py
   ```

3. Open [http://localhost:3000](http://localhost:3000) and go to **Tracing -> Traces** to view the logged LLM call.

---

### Option B: OpenAI Drop-in Replacement

If you use the `openai` Python library, Langfuse provides a drop-in wrapper that automatically tracks prompts, completions, tokens, and latency:

```bash
pip install langfuse openai
```

```python
import os
from langfuse.openai import openai

# Set Langfuse environment variables
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-local-demo-1234567890"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-local-demo-1234567890"
os.environ["LANGFUSE_HOST"] = "http://localhost:3000"

# Make OpenAI calls as usual
response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
    name="greeting-chat",
    metadata={"user_type": "tester"}
)

print(response.choices[0].message.content)
```

---

### Option C: LangChain Integration

Langfuse provides native callback handlers for LangChain:

```bash
pip install langfuse langchain-community
```

```python
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler(
    public_key="pk-lf-local-demo-1234567890",
    secret_key="sk-lf-local-demo-1234567890",
    host="http://localhost:3000"
)

# Pass to any LangChain invoke or chain:
# chain.invoke({"input": "..."}, config={"callbacks": [langfuse_handler]})
```

---

### Option D: Function Decorator (`@observe`)

Decorate any Python function to automatically trace inputs, outputs, and execution time:

```python
from langfuse.decorators import observe, langfuse_context

@observe()
def run_rag_pipeline(query: str):
    # Any LLM calls inside will automatically be nested under this trace
    langfuse_context.update_current_trace(
        user_id="user_42",
        tags=["rag", "local"]
    )
    return "answer"
```

---

## Management Commands

| Action | Command |
| :--- | :--- |
| **Start in background** | `docker compose up -d` |
| **View logs (all services)** | `docker compose logs -f` |
| **View web logs only** | `docker compose logs -f langfuse-web` |
| **View worker logs only** | `docker compose logs -f langfuse-worker` |
| **Check container health** | `docker compose ps` |
| **Stop services** | `docker compose stop` |
| **Restart services** | `docker compose restart` |
| **Tear down (preserve data)** | `docker compose down` |
| **Tear down & wipe data** | `docker compose down -v` |

---

## Exposed Ports Overview

| Service | Host Port | Bound IP | Description |
| :--- | :--- | :--- | :--- |
| `langfuse-web` | `3000` | `0.0.0.0` | Langfuse Web Dashboard & Ingestion API |
| `minio` (S3 API) | `9090` | `0.0.0.0` | Object storage S3 API |
| `minio` (Console) | `9091` | `127.0.0.1` | MinIO web console |
| `clickhouse` | `8123` / `9000` | `127.0.0.1` | HTTP / Native ClickHouse ports |
| `postgres` | `5432` | `127.0.0.1` | PostgreSQL database |
| `redis` | `6379` | `127.0.0.1` | Redis cache and queue |
| `langfuse-worker`| `3030` | `127.0.0.1` | Internal background worker port |
