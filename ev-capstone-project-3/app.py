"""
Flask Customer Support RAG Application.
Exposes REST endpoints for session management, conversation history,
and RAG-powered answers using LangChain, LangGraph, and SQLite.
"""

import os
import sys
import uuid
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)

# Load environment variables
load_dotenv(os.path.join(CURRENT_DIR, ".env"))
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(os.path.join(PARENT_DIR, "langchain-app", ".env"))

import database
import rag_engine
import seed_data

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Ensure database is seeded and RAG engine initialized on startup
with app.app_context():
    database.init_db()
    if database.count_tickets() == 0:
        print("[Startup] Seeding database with historical support cases...")
        seed_data.seed_database()
    rag_engine.init_rag_engine()


# ==============================================================================
# HTML Web UI Routes
# ==============================================================================

@app.route("/")
def index():
    """Renders the main customer support chat interface."""
    products = database.get_distinct_products()
    ticket_count = database.count_tickets()
    return render_template(
        "index.html",
        products=products,
        ticket_count=ticket_count
    )


# ==============================================================================
# API Endpoints
# ==============================================================================

@app.route("/api/products", methods=["GET"])
def get_products():
    """Returns available software products and sample questions."""
    products = database.get_distinct_products()
    product_meta = {
        "CloudSync Pro": {
            "icon": "bi-cloud-check-fill",
            "tagline": "Enterprise Cloud File Sync & Collaboration",
            "sample_questions": [
                "My client is stuck on 'Connecting to sync engine' on macOS Sonoma.",
                "How do we handle conflicted copy files when two people edit offline?",
                "Can we enable local Wi-Fi LAN sync to avoid eating our office internet?",
                "I deleted 100GB of files but storage quota still says 98% full."
            ]
        },
        "DataPulse Analytics": {
            "icon": "bi-bar-chart-line-fill",
            "tagline": "Real-time BI Dashboards & Enterprise Reporting",
            "sample_questions": [
                "PostgreSQL connector fails with SSL certificate verify error on AWS RDS.",
                "Scheduled PDF report email is arriving with blank charts.",
                "Custom SQL query on Snowflake times out after 60 seconds.",
                "How do I deactivate dormant users to free up license seats?"
            ]
        },
        "SecureAuth Gateway": {
            "icon": "bi-shield-lock-fill",
            "tagline": "Identity Provider, SAML 2.0, SSO & Zero-Trust MFA",
            "sample_questions": [
                "Okta SAML SSO login fails with Audience URI mismatch.",
                "User lost their MFA phone authenticator and is locked out.",
                "Users get logged out every 15 mins through our Nginx reverse proxy.",
                "SCIM deprovisioning doesn't revoke active OAuth2 refresh tokens."
            ]
        },
        "DevFlow CI/CD": {
            "icon": "bi-cpu-fill",
            "tagline": "Automated Build Pipelines & Container Deployment",
            "sample_questions": [
                "Pipeline fails with 'Cannot connect to the Docker daemon at /var/run/docker.sock'.",
                "Why is our $PROD_DEPLOY_KEY variable empty on our staging branch?",
                "Every CI run re-downloads all npm node_modules; how to cache properly?",
                "Kubernetes deploy step fails with ImagePullBackOff 401 Unauthorized."
            ]
        }
    }
    return jsonify({
        "products": products,
        "metadata": product_meta
    })


@app.route("/api/sessions/start", methods=["POST"])
def start_session():
    """
    Starts a new support conversation session.
    Expects JSON: { name, email, product, initial_query (optional) }
    """
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    product = data.get("product", "").strip()
    initial_query = data.get("initial_query", "").strip()

    if not name or not email or not product:
        return jsonify({"error": "Name, email, and product are required fields."}), 400

    session_id = str(uuid.uuid4())
    session = database.create_session(session_id, name, email, product)

    messages = []
    # If the user supplied an initial query upon starting the session, process it immediately
    if initial_query:
        # Save user message
        user_msg = database.add_message(session_id, "user", initial_query)
        messages.append(user_msg)

        # Process through RAG
        rag_output = rag_engine.process_support_query(
            session_id=session_id,
            customer_name=name,
            customer_email=email,
            product=product,
            query=initial_query,
            history=[]
        )

        # Save assistant message
        bot_msg = database.add_message(
            session_id=session_id,
            sender="assistant",
            message=rag_output["response"],
            rag_sources=rag_output.get("sources", [])
        )
        messages.append(bot_msg)

    return jsonify({
        "success": True,
        "session": session,
        "messages": messages
    })


@app.route("/api/sessions/<session_id>/message", methods=["POST"])
def send_message(session_id: str):
    """
    Processes a new message in an active session, maintains history,
    and returns RAG-grounded response.
    """
    session = database.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    if session.get("status") == "ended":
        return jsonify({
            "error": "This conversation has been closed. Please start a new session to continue chatting."
        }), 400

    data = request.get_json() or {}
    message_text = data.get("message", "").strip()
    if not message_text:
        return jsonify({"error": "Message text cannot be empty."}), 400

    # Retrieve existing message history for conversational context
    history = database.get_session_messages(session_id)

    # Save current user message
    user_msg = database.add_message(session_id, "user", message_text)

    # Process through RAG engine
    rag_output = rag_engine.process_support_query(
        session_id=session_id,
        customer_name=session.get("customer_name", "Customer"),
        customer_email=session.get("customer_email", ""),
        product=session.get("product", ""),
        query=message_text,
        history=history
    )

    # Save assistant message with RAG sources
    bot_msg = database.add_message(
        session_id=session_id,
        sender="assistant",
        message=rag_output["response"],
        rag_sources=rag_output.get("sources", [])
    )

    return jsonify({
        "success": True,
        "user_message": user_msg,
        "assistant_message": bot_msg,
        "sources": rag_output.get("sources", [])
    })


@app.route("/api/sessions/<session_id>/end", methods=["POST"])
def close_session(session_id: str):
    """Ends the customer support conversation session."""
    session = database.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    success = database.end_session(session_id)
    updated_session = database.get_session(session_id)

    # Optionally add a system closing note
    database.add_message(
        session_id=session_id,
        sender="assistant",
        message="*This conversation has been ended by the customer. Thank you for contacting technical support!*",
        rag_sources=[]
    )

    return jsonify({
        "success": success,
        "session": updated_session
    })


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session_details(session_id: str):
    """Returns session metadata and full message history."""
    session = database.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    messages = database.get_session_messages(session_id)
    return jsonify({
        "session": session,
        "messages": messages
    })


@app.route("/api/sessions", methods=["GET"])
def list_all_sessions():
    """Lists past support conversation sessions."""
    sessions = database.list_sessions(limit=50)
    return jsonify({"sessions": sessions})


@app.route("/api/historical-tickets", methods=["GET"])
def list_historical_tickets():
    """Inspects the historical knowledge base tickets stored in the SQLite DB."""
    product = request.args.get("product")
    tickets = database.get_all_tickets_for_product(product)
    # Exclude raw embedding float array from JSON response to keep payload light
    sanitized = []
    for t in tickets:
        item = {k: v for k, v in t.items() if k != "embedding"}
        item["has_embedding"] = bool(t.get("embedding"))
        sanitized.append(item)
    return jsonify({
        "total": len(sanitized),
        "tickets": sanitized
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    print(f"[App] Starting Flask Customer Support RAG Server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
