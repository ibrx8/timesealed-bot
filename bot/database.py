"""SQLite storage layer: topics and dated entries."""

import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------- Topics ----------

def add_topic(name: str) -> bool:
    """Returns False if the topic already exists."""
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO topics (name, created_at) VALUES (?, ?)",
                (name, datetime.now().isoformat()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def delete_topic(name: str) -> bool:
    """Deletes a topic and all of its entries. Returns False if not found."""
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM entries WHERE topic_id = ?", (row["id"],))
        conn.execute("DELETE FROM topics WHERE id = ?", (row["id"],))
        return True


def list_topics():
    with get_conn() as conn:
        rows = conn.execute("SELECT name FROM topics ORDER BY name").fetchall()
        return [r["name"] for r in rows]


def get_topic_id(name: str):
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()
        return row["id"] if row else None


# ---------- Entries ----------

def add_entry(topic_name: str, content: str, when: datetime = None) -> int:
    when = when or datetime.now()
    with get_conn() as conn:
        topic = conn.execute(
            "SELECT id FROM topics WHERE name = ?", (topic_name,)
        ).fetchone()
        if not topic:
            raise ValueError(f"Topic '{topic_name}' does not exist")
        cur = conn.execute(
            "INSERT INTO entries (topic_id, content, created_at) VALUES (?, ?, ?)",
            (topic["id"], content, when.isoformat()),
        )
        return cur.lastrowid


def get_last_entry(topic_name: str):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT e.id, e.content, e.created_at FROM entries e
               JOIN topics t ON t.id = e.topic_id
               WHERE t.name = ?
               ORDER BY e.id DESC LIMIT 1""",
            (topic_name,),
        ).fetchone()
        return dict(row) if row else None


def delete_entry(entry_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))


def update_entry(entry_id: int, new_content: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE entries SET content = ? WHERE id = ?", (new_content, entry_id)
        )


def search_entries(keyword: str):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT t.name AS topic, e.content, e.created_at FROM entries e
               JOIN topics t ON t.id = e.topic_id
               WHERE e.content LIKE ?
               ORDER BY e.created_at DESC""",
            (f"%{keyword}%",),
        ).fetchall()
        return [dict(r) for r in rows]


def entries_on_this_day(month: int, day: int, exclude_year: int):
    """Entries from previous years matching today's month/day."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT t.name AS topic, e.content, e.created_at FROM entries e
               JOIN topics t ON t.id = e.topic_id
               WHERE strftime('%m', e.created_at) = ?
                 AND strftime('%d', e.created_at) = ?
                 AND strftime('%Y', e.created_at) != ?
               ORDER BY e.created_at DESC""",
            (f"{month:02d}", f"{day:02d}", str(exclude_year)),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_entries(topic_name: str = None):
    """All entries, optionally filtered by topic, ordered chronologically."""
    with get_conn() as conn:
        if topic_name:
            rows = conn.execute(
                """SELECT t.name AS topic, e.content, e.created_at FROM entries e
                   JOIN topics t ON t.id = e.topic_id
                   WHERE t.name = ?
                   ORDER BY e.created_at ASC""",
                (topic_name,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT t.name AS topic, e.content, e.created_at FROM entries e
                   JOIN topics t ON t.id = e.topic_id
                   ORDER BY e.created_at ASC"""
            ).fetchall()
        return [dict(r) for r in rows]


def stats():
    with get_conn() as conn:
        topic_count = conn.execute("SELECT COUNT(*) c FROM topics").fetchone()["c"]
        entry_count = conn.execute("SELECT COUNT(*) c FROM entries").fetchone()["c"]
        word_count = 0
        for row in conn.execute("SELECT content FROM entries"):
            word_count += len(row["content"].split())
        per_topic = conn.execute(
            """SELECT t.name AS topic, COUNT(e.id) AS n FROM topics t
               LEFT JOIN entries e ON e.topic_id = t.id
               GROUP BY t.name ORDER BY t.name"""
        ).fetchall()
        return {
            "topics": topic_count,
            "entries": entry_count,
            "words": word_count,
            "per_topic": {r["topic"]: r["n"] for r in per_topic},
        }
