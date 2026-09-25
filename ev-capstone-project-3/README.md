# OmniSupport AI - Intelligent Customer Support RAG Application

A Python Flask-based customer support application powered by **LangChain**, **LangGraph**, **OpenAI LLM & Embeddings**, and **Langfuse Observability**. It grounds AI support responses in verified historical customer support queries and technical resolutions stored in a SQLite knowledge base.

---

## 🌟 Key Features

1. **Historical Support Knowledge Base (RAG Source)**:
   - Contains verified past customer queries and technical resolutions across 4 software products:
     - 📁 **CloudSync Pro**: Desktop sync client permissions, conflicted copy resolution, LAN sync, quota purge, long path Windows registry, E2EE recovery, headless Linux daemon.
     - 📊 **DataPulse Analytics**: AWS RDS PostgreSQL SSL certificates, headless PDF render timeouts, Snowflake query timeouts, kiosk WebSocket keepalive, license seat deactivation, window functions, REST API rate limiting.
     - 🔐 **SecureAuth Gateway**: Okta SAML 2.0 Audience URI mismatch, emergency MFA bypass codes, Nginx reverse proxy IP binding, LDAPS certificates, SCIM token revocation, WebAuthn FIDO2 keys, custom SSL domains.
     - 🚀 **DevFlow CI/CD**: Docker-in-Docker daemon socket, self-hosted runner auto-restart, branch-protected secret variables, lockfile build caching, Kubernetes ECR image pull secrets, GitHub webhooks, automated canary rollback.
   - Precomputed vector embeddings (`text-embedding-3-small`) stored alongside ticket records in SQLite for high-precision semantic retrieval.

2. **Customer Identification & Product Selection**:
   - Web UI for customers to submit their Full Name, Work Email, Product selection, and initial inquiry.
   - Dynamic sample questions tailored to each software product for quick one-click testing.

3. **LangGraph Multi-Stage RAG Pipeline**:
   - **Contextualize Node**: Reformulates multi-turn user follow-up questions into standalone search queries preserving previous conversation context.
   - **Retrieve Node**: Filters by target software product and performs cosine vector similarity + keyword scoring against the historical database.
   - **Generate Node**: Synthesizes verified support procedures into formatted markdown answers, citing historical ticket codes (e.g. `[Ref: CSP-101]`).
   - **Observability**: Instrumented with Langfuse `@observe` for end-to-end tracing.

4. **Session-Based Conversation Lifecycle**:
   - Each customer conversation is a distinct tracked session (`session_id`).
   - Starts when customer submits details and clicks **"Start Conversation with Support Bot"**.
   - **"End Conversation"** button cleanly closes the session and marks it as ended.
   - Prevents sending messages to closed sessions.

5. **Persistent Conversation History & Transcripts**:
   - All user queries, AI responses, and RAG sources are persisted in SQLite.
   - Multi-turn context is maintained across subsequent questions in the session.
   - **Past Sessions Modal**: Browse past conversations and reload full transcripts.
   - **Export Transcript**: One-click download of the complete conversation transcript (`.txt`).
   - **Knowledge Base Explorer**: Inspect the raw historical tickets stored in the database.

---

## 🏗️ Architecture

```
                                  +---------------------------------------+
                                  |            Web Browser                |
                                  |  (Bootstrap 5, Marked.js, Highlight)  |
                                  +-------------------+-------------------+
                                                      |  HTTP / REST
                                                      v
                                  +---------------------------------------+
                                  |         Flask Web Server (app.py)     |
                                  +-------------------+-------------------+
                                                      |
                    +---------------------------------+---------------------------------+
                    |                                                                   |
                    v                                                                   v
     +------------------------------+                                    +------------------------------+
     |     SQLite Database (DB)     |                                    |       LangGraph RAG Engine   |
     |   - historical_support_tickets | <------------------------------+ |   1. Query Contextualizer    |
     |   - support_sessions         |                                    |   2. Vector Retriever        |
     |   - session_messages         |                                    |   3. Solution Generator      |
     +------------------------------+                                    +--------------+---------------+
                                                                                        |
                                                                        +---------------+---------------+
                                                                        |                               |
                                                                        v                               v
                                                         +------------------------------+ +------------------------------+
                                                         |     OpenAI API               | |    Langfuse Observability    |
                                                         |  - gpt-4o-mini               | |  - @observe Tracing          |
                                                         |  - text-embedding-3-small    | |  - Latency & Token metrics   |
                                                         +------------------------------+ +------------------------------+
```

---

## 📁 Project Structure

```
flask-support-app/
├── app.py                  # Flask web application and REST API endpoints
├── database.py             # SQLite schema, session handling, messages, ticket queries
├── rag_engine.py           # LangGraph StateGraph, vector retrieval, and OpenAI generation
├── seed_data.py            # Historical ticket knowledge base and embedding generator
├── test_app.py             # Automated unit tests for all endpoints and RAG flows
├── requirements.txt        # Python package dependencies
├── .env                    # Environment configuration (OpenAI & Langfuse)
├── templates/
│   └── index.html          # Responsive single-page application UI
└── static/
    ├── css/
    │   └── style.css       # Custom styling for chat bubbles, sources, and animations
    └── js/
        └── chat.js         # Frontend JavaScript for sessions, API calls, and Markdown
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.12)
- Virtual environment with dependencies installed

### 2. Configuration
Ensure `.env` contains your OpenAI credentials (automatically loaded from `langchain-app/.env` if present):
```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL_NAME=gpt-4o-mini

# Optional Langfuse configuration
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
```

### 3. Initialize Database & Embeddings
```bash
cd flask-support-app
python seed_data.py
```
*Note: This creates `support_rag.db` and computes vector embeddings for all 28 historical tickets across 4 software products.*

### 4. Run the Flask Web Application
```bash
python app.py
```
The server will start at:
👉 **`http://localhost:5001`**

### 5. Run the Automated Test Suite
```bash
python test_app.py
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI interface |
| `GET` | `/api/products` | Lists software products and sample questions |
| `POST` | `/api/sessions/start` | Creates new session, answers initial query via RAG |
| `POST` | `/api/sessions/<id>/message` | Submits follow-up query, maintains history, returns RAG response |
| `POST` | `/api/sessions/<id>/end` | Closes active conversation session |
| `GET` | `/api/sessions/<id>` | Returns session details and full message history |
| `GET` | `/api/sessions` | Lists recent conversation sessions |
| `GET` | `/api/historical-tickets` | Browses historical support tickets in the database |
