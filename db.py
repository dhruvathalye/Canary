"""SQLite storage for the deception platform.

Two tables:
  tokens  - the bait we plant (a decoy file, fake login, tracking link, ...)
  events  - every time a piece of bait gets triggered (= a possible breach)

Nothing fancy on purpose. One file (deception.db) is the whole database.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "deception.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read rows like dicts: row["name"]
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            kind        TEXT NOT NULL,      -- 'link' | 'file' | 'login'
            created_at  TEXT NOT NULL,
            note        TEXT,
            company     TEXT,
            location    TEXT,
            email       TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id    TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            ip          TEXT,
            geo         TEXT,
            user_agent  TEXT,
            explanation TEXT               -- plain-English action plan for the owner
        );
        """
    )
    # Migration: add new columns to databases created before they existed.
    for col in ("company", "location", "email"):
        try:
            conn.execute(f"ALTER TABLE tokens ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists -> fine
    conn.commit()
    conn.close()


# ----- tokens -----

def create_token(token_id, name, kind, created_at, note="",
                 company="", location="", email=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO tokens (id, name, kind, created_at, note, company, location, email) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (token_id, name, kind, created_at, note, company, location, email),
    )
    conn.commit()
    conn.close()


def list_tokens():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tokens ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_token(token_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ----- events -----

def create_event(token_id, triggered_at, ip, geo, user_agent):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO events (token_id, triggered_at, ip, geo, user_agent) "
        "VALUES (?, ?, ?, ?, ?)",
        (token_id, triggered_at, ip, geo, user_agent),
    )
    event_id = cur.lastrowid
    conn.commit()
    conn.close()
    return event_id


def set_event_explanation(event_id, explanation):
    conn = get_conn()
    conn.execute(
        "UPDATE events SET explanation = ? WHERE id = ?", (explanation, event_id)
    )
    conn.commit()
    conn.close()


def list_events():
    """Most recent breach alerts first, joined with the token name."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT events.*, tokens.name AS token_name, tokens.kind AS token_kind,
               tokens.created_at AS token_created_at
        FROM events
        JOIN tokens ON tokens.id = events.token_id
        ORDER BY events.id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
