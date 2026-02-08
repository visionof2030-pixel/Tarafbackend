# database.py
import sqlite3
import os
from datetime import datetime

DB_PATH = "/tmp/database.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    os.makedirs("/tmp", exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activation_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        is_active INTEGER,
        created_at TEXT,
        expires_at TEXT,
        usage_limit INTEGER,
        usage_count INTEGER,
        last_used_at TEXT
    )
    """)
    conn.commit()
    conn.close()