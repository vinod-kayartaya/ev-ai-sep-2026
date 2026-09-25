"""
Database access layer for Enterprise Operations Assistant.
Provides clean query and persistence functions for SQLite.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.config import DATABASE_PATH


def get_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_customer(customer_id: str, db_path: str = DATABASE_PATH) -> Optional[Dict[str, Any]]:
    clean_id = customer_id.strip().upper()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (clean_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_invoice(invoice_id: str, db_path: str = DATABASE_PATH) -> Optional[Dict[str, Any]]:
    clean_id = invoice_id.strip().upper()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE invoice_id = ?", (clean_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_customer_invoices(customer_id: str, db_path: str = DATABASE_PATH) -> List[Dict[str, Any]]:
    clean_id = customer_id.strip().upper()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE customer_id = ? ORDER BY invoice_date DESC", (clean_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def insert_financial_adjustment(
    customer_id: str,
    invoice_id: str,
    amount: float,
    reason: str,
    status: str = "Pending",
    db_path: str = DATABASE_PATH,
) -> str:
    """Inserts a financial adjustment record and returns adjustment_id."""
    clean_cust = customer_id.strip().upper()
    clean_inv = invoice_id.strip().upper()
    adj_id = f"ADJ{uuid.uuid4().hex[:6].upper()}"
    created_at = datetime.now().isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO adjustments (adjustment_id, customer_id, invoice_id, amount, status, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (adj_id, clean_cust, clean_inv, amount, status, reason, created_at),
        )
        conn.commit()
    return adj_id


def update_adjustment(
    adjustment_id: str,
    status: str,
    db_path: str = DATABASE_PATH,
) -> bool:
    """Updates the status of an adjustment (e.g. Approved, Rejected)."""
    clean_id = adjustment_id.strip().upper()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE adjustments SET status = ? WHERE adjustment_id = ?",
            (status, clean_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def insert_resolution_log(
    customer_id: str,
    complaint: str,
    invoice_id: Optional[str],
    investigation_result: str,
    reconciliation_result: str,
    recommended_resolution: str,
    financial_adjustment_amount: float = 0.0,
    approval_decision: Optional[str] = None,
    final_status: str = "Completed",
    db_path: str = DATABASE_PATH,
) -> int:
    """Logs the resolution of a complaint to the auditable log table."""
    timestamp = datetime.now().isoformat()
    clean_cust = customer_id.strip().upper() if customer_id else "UNKNOWN"
    clean_inv = invoice_id.strip().upper() if invoice_id else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO resolution_logs (
                customer_id, complaint, invoice_id, investigation_result,
                reconciliation_result, recommended_resolution,
                financial_adjustment_amount, approval_decision, final_status, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_cust,
                complaint,
                clean_inv,
                investigation_result,
                reconciliation_result,
                recommended_resolution,
                financial_adjustment_amount,
                approval_decision,
                final_status,
                timestamp,
            ),
        )
        conn.commit()
        return cursor.lastrowid
