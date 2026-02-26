import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).with_name("bot.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                tg_name TEXT,
                ig_link TEXT,
                real_name TEXT,
                phone TEXT,
                likes INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 0,
                created_at TEXT,
                last_active TEXT
            )
            """
        )
        _ensure_column(conn, "users", "last_active", "TEXT")
        conn.commit()


def _ensure_column(conn, table_name: str, column_name: str, column_type: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cur.fetchall()]
    if column_name not in cols:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def upsert_user(tg_id, username, tg_name):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))
        if cur.fetchone():
            cur.execute(
                "UPDATE users SET username=?, tg_name=?, last_active=? WHERE tg_id=?",
                (username, tg_name, now, tg_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO users (tg_id, username, tg_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tg_id, username, tg_name, now, now),
            )
        conn.commit()


def touch_user(tg_id):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_active=? WHERE tg_id=?", (now, tg_id))
        conn.commit()


def update_instagram(tg_id, ig_link):
    with get_conn() as conn:
        conn.execute("UPDATE users SET ig_link=? WHERE tg_id=?", (ig_link, tg_id))
        conn.commit()


def update_real_name(tg_id, real_name):
    with get_conn() as conn:
        conn.execute("UPDATE users SET real_name=? WHERE tg_id=?", (real_name, tg_id))
        conn.commit()


def update_phone(tg_id, phone):
    with get_conn() as conn:
        conn.execute("UPDATE users SET phone=? WHERE tg_id=?", (phone, tg_id))
        conn.commit()


def set_metrics(tg_id, likes, views):
    rating = likes + views
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET likes=?, views=?, rating=? WHERE tg_id=?",
            (likes, views, rating, tg_id),
        )
        conn.commit()
    return rating


def get_user(tg_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        row = cur.fetchone()
    return row


def get_all_users():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY created_at ASC")
        rows = cur.fetchall()
    return rows


def get_active_users(days: int):
    threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE last_active IS NOT NULL AND last_active >= ? ORDER BY created_at ASC",
            (threshold,),
        )
        rows = cur.fetchall()
    return rows
