import sqlite3
import os
from datetime import datetime

DB_PATH = "database/website_analyst.db"


def init_db():
    """
    Create tables if they don't exist.
    Two tables:
    - analyzed_urls: tracks which URLs a session has analyzed
    - chat_history: stores all messages per session and URL
    """
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table 1: Track all URLs analyzed by each session
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyzed_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            url TEXT NOT NULL,
            page_title TEXT,
            analyzed_at TEXT NOT NULL
        )
    """)

    # Table 2: Store all chat messages per session and URL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            url TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Database ready")


def save_analyzed_url(session_id, url, page_title):
    """Save a URL that was analyzed in this session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Only save if not already saved for this session
    cursor.execute("""
        SELECT id FROM analyzed_urls
        WHERE session_id = ? AND url = ?
    """, (session_id, url))

    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO analyzed_urls (session_id, url, page_title, analyzed_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, url, page_title, datetime.now().isoformat()))
        conn.commit()

    conn.close()


def save_message(session_id, url, role, message):
    """Save a single chat message"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chat_history (session_id, url, role, message, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, url, role, message, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_chat_history(session_id, url):
    """Get all messages for a specific session and URL"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, message, created_at
        FROM chat_history
        WHERE session_id = ? AND url = ?
        ORDER BY created_at ASC
    """, (session_id, url))

    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "role": row[0],
            "content": row[1],
            "created_at": row[2]
        })

    return history


def get_analyzed_urls(session_id):
    """Get all URLs analyzed by this session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT url, page_title, analyzed_at
        FROM analyzed_urls
        WHERE session_id = ?
        ORDER BY analyzed_at DESC
    """, (session_id,))

    rows = cursor.fetchall()
    conn.close()

    urls = []
    for row in rows:
        urls.append({
            "url": row[0],
            "page_title": row[1],
            "analyzed_at": row[2]
        })

    return urls


def get_all_sessions():
    """Get all unique sessions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT session_id, MIN(analyzed_at) as started_at
        FROM analyzed_urls
        GROUP BY session_id
        ORDER BY started_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [{"session_id": row[0], "started_at": row[1]} for row in rows]
