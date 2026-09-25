"""
Database module for the Customer Support RAG Flask Application.
Manages SQLite connection, schema, historical tickets, sessions, and messages.
"""

import json
import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "support_rag.db")


def get_db_connection() -> sqlite3.Connection:
    """Creates a connection to the SQLite database with row_factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables for historical tickets, sessions, and messages."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Historical Customer Support Tickets (RAG Source)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_code TEXT UNIQUE NOT NULL,
                product TEXT NOT NULL,
                category TEXT NOT NULL,
                customer_query TEXT NOT NULL,
                support_response TEXT NOT NULL,
                resolution_summary TEXT NOT NULL,
                embedding TEXT,  -- JSON serialized list of floats
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_product ON historical_support_tickets(product);")

        # 2. Customer Chat Sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_sessions (
                session_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                product TEXT NOT NULL,
                status TEXT DEFAULT 'active', -- 'active' or 'ended'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_email ON support_sessions(customer_email);")

        # 3. Conversation Messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL, -- 'user' or 'assistant'
                message TEXT NOT NULL,
                rag_sources TEXT, -- JSON serialized list of retrieved historical tickets
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES support_sessions(session_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON session_messages(session_id);")

        conn.commit()


# --- Session Operations ---

def create_session(session_id: str, name: str, email: str, product: str) -> Dict[str, Any]:
    """Creates a new customer session."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO support_sessions (session_id, customer_name, customer_email, product, status, created_at)
            VALUES (?, ?, ?, ?, 'active', ?)
            """,
            (session_id, name.strip(), email.strip(), product.strip(), now)
        )
        conn.commit()
    return get_session(session_id)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves session details by session_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM support_sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def end_session(session_id: str) -> bool:
    """Marks a session as ended."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE support_sessions
            SET status = 'ended', ended_at = ?
            WHERE session_id = ?
            """,
            (now, session_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def list_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """Lists recent support sessions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.*, 
                   (SELECT COUNT(*) FROM session_messages m WHERE m.session_id = s.session_id) as message_count,
                   (SELECT m.message FROM session_messages m WHERE m.session_id = s.session_id ORDER BY m.id DESC LIMIT 1) as last_message
            FROM support_sessions s
            ORDER BY s.created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# --- Message Operations ---

def add_message(session_id: str, sender: str, message: str, rag_sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Adds a message to a session."""
    sources_json = json.dumps(rag_sources) if rag_sources else None
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO session_messages (session_id, sender, message, rag_sources, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, sender, message, sources_json, now)
        )
        msg_id = cursor.lastrowid
        conn.commit()
        return {
            "id": msg_id,
            "session_id": session_id,
            "sender": sender,
            "message": message,
            "rag_sources": rag_sources or [],
            "timestamp": now
        }


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Gets all messages for a session in chronological order."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM session_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get("rag_sources"):
                try:
                    d["rag_sources"] = json.loads(d["rag_sources"])
                except Exception:
                    d["rag_sources"] = []
            else:
                d["rag_sources"] = []
            result.append(d)
        return result


# --- Historical Tickets (RAG Source) ---

def insert_ticket(ticket_code: str, product: str, category: str, 
                  customer_query: str, support_response: str, 
                  resolution_summary: str, embedding: Optional[List[float]] = None) -> int:
    """Inserts a historical customer support ticket."""
    embedding_json = json.dumps(embedding) if embedding else None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO historical_support_tickets 
            (ticket_code, product, category, customer_query, support_response, resolution_summary, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket_code, product, category, customer_query, support_response, resolution_summary, embedding_json)
        )
        conn.commit()
        return cursor.lastrowid


def count_tickets() -> int:
    """Returns total number of historical tickets in DB."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM historical_support_tickets")
        return cursor.fetchone()[0]


def get_all_tickets_for_product(product: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches all tickets, optionally filtered by product, including parsed embeddings."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if product:
            cursor.execute(
                "SELECT * FROM historical_support_tickets WHERE LOWER(product) = LOWER(?)",
                (product.strip(),)
            )
        else:
            cursor.execute("SELECT * FROM historical_support_tickets")
        rows = cursor.fetchall()
        tickets = []
        for row in rows:
            d = dict(row)
            if d.get("embedding"):
                try:
                    d["embedding"] = json.loads(d["embedding"])
                except Exception:
                    d["embedding"] = None
            tickets.append(d)
        return tickets


def get_distinct_products() -> List[str]:
    """Returns list of distinct software products in the historical database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT product FROM historical_support_tickets ORDER BY product ASC")
        return [row[0] for row in cursor.fetchall()]
