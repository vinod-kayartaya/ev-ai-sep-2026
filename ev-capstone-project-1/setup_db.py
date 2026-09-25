"""
Database setup and seed script for Enterprise Operations Assistant.
Creates SQLite tables for customers, invoices, adjustments, and resolution_logs.
"""

import os
import sqlite3
from datetime import datetime

DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "operations.db")


def get_db_connection(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH):
    """Initializes tables and seeds initial operational data."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Drop existing tables to allow clean recreation
    cursor.execute("DROP TABLE IF EXISTS resolution_logs")
    cursor.execute("DROP TABLE IF EXISTS adjustments")
    cursor.execute("DROP TABLE IF EXISTS invoices")
    cursor.execute("DROP TABLE IF EXISTS customers")

    # 1. Customers Table
    cursor.execute("""
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            account_status TEXT NOT NULL
        )
    """)

    # 2. Invoices Table
    cursor.execute("""
        CREATE TABLE invoices (
            invoice_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            invoice_amount REAL NOT NULL,
            invoice_status TEXT NOT NULL,
            invoice_date TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        )
    """)

    # 3. Adjustments Table
    cursor.execute("""
        CREATE TABLE adjustments (
            adjustment_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
            FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id)
        )
    """)

    # 4. Resolution Logs Table (Auditable record)
    cursor.execute("""
        CREATE TABLE resolution_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            complaint TEXT NOT NULL,
            invoice_id TEXT,
            investigation_result TEXT,
            reconciliation_result TEXT,
            recommended_resolution TEXT,
            financial_adjustment_amount REAL DEFAULT 0.0,
            approval_decision TEXT,
            final_status TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    # Seed Customers
    customers = [
        ("C1024", "Rahul Sharma", "rahul@example.com", "Active"),
        ("C1025", "Priya Patel", "priya@example.com", "Active"),
        ("C1026", "Amit Verma", "amit@example.com", "Active"),
        ("C1027", "Sunita Rao", "sunita@example.com", "Active"),
        ("C1028", "Vikram Singh", "vikram@example.com", "Active"),
    ]
    cursor.executemany(
        "INSERT INTO customers (customer_id, name, email, account_status) VALUES (?, ?, ?, ?)",
        customers,
    )

    # Seed Invoices
    # Scenario 1: C1024 - INV10045 internal 12,500 vs external 10,000 (mismatch 2,500)
    # Scenario 2: C1025 - INV10046 (3,000) & INV10046_DUP (3,000) duplicate charges
    # Scenario 3: C1026 - INV10047 (7,500) matches external (7,500)
    # Scenario 4: C1027 - INV10048 internal 18,000 vs external 14,500 (adjustment 3,500)
    # Scenario 5: C1028 - INV10049 internal 5,000 vs external 5,000
    invoices = [
        ("INV10045", "C1024", 12500.0, "Paid", "2026-09-20"),
        ("INV10046", "C1025", 3000.0, "Paid", "2026-09-21"),
        ("INV10046_DUP", "C1025", 3000.0, "Paid", "2026-09-21"),
        ("INV10047", "C1026", 7500.0, "Paid", "2026-09-22"),
        ("INV10048", "C1027", 18000.0, "Paid", "2026-09-23"),
        ("INV10049", "C1028", 5000.0, "Paid", "2026-09-24"),
    ]
    cursor.executemany(
        "INSERT INTO invoices (invoice_id, customer_id, invoice_amount, invoice_status, invoice_date) VALUES (?, ?, ?, ?, ?)",
        invoices,
    )

    conn.commit()
    conn.close()
    print(f"Database successfully initialized at {db_path} with sample data.")


if __name__ == "__main__":
    init_db()
