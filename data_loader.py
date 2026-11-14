# db.py
# Explain it simply: this module creates and updates the local SQLite database.
# It stores readings, events, alerts and notifications for the dashboard.

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from config import SQLITE_DB_PATH

DB_PATH = Path(__file__).resolve().parent / SQLITE_DB_PATH


def connect_db(path: str | None = None):
    db_path = Path(path) if path else DB_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            astronaut_id TEXT,
            ts TEXT,
            signal TEXT,
            value REAL,
            source TEXT,
            quality TEXT,
            sync_pending INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            astronaut_id TEXT,
            ts TEXT,
            kind TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            astronaut_id TEXT,
            ts TEXT,
            level TEXT,
            title TEXT,
            what TEXT,
            why TEXT,
            todo TEXT,
            signals_json TEXT,
            acknowledged INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            recipient_role TEXT,
            astronaut_id TEXT,
            message TEXT,
            sync_pending INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()


def insert_reading(conn: sqlite3.Connection, record: dict):
    conn.execute(
        """
        INSERT INTO readings (astronaut_id, ts, signal, value, source, quality, sync_pending)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("astronaut_id"),
            record.get("ts"),
            record.get("signal"),
            float(record.get("value", 0.0)),
            record.get("source", "simulated"),
            record.get("quality", "demo"),
            int(record.get("sync_pending", 0)),
        ),
    )
    conn.commit()


def insert_event(conn: sqlite3.Connection, astronaut_id: str, ts: str, kind: str):
    conn.execute(
        "INSERT INTO events (astronaut_id, ts, kind) VALUES (?, ?, ?)",
        (astronaut_id, ts, kind),
    )
    conn.commit()


def insert_alert(
    conn: sqlite3.Connection,
    astronaut_id: str,
    ts: str,
    level: str,
    title: str,
    what: str,
    why: str,
    todo: str,
    signals_json: dict | list | str,
    acknowledged: int = 0,
):
    payload = signals_json
    if isinstance(payload, (dict, list)):
        payload = json.dumps(payload)
    conn.execute(
        """
        INSERT INTO alerts (astronaut_id, ts, level, title, what, why, todo, signals_json, acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (astronaut_id, ts, level, title, what, why, todo, payload, acknowledged),
    )
    conn.commit()


def insert_notification(
    conn: sqlite3.Connection,
    ts: str,
    recipient_role: str,
    astronaut_id: str,
    message: str,
    sync_pending: int = 0,
):
    conn.execute(
        """
        INSERT INTO notifications (ts, recipient_role, astronaut_id, message, sync_pending)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ts, recipient_role, astronaut_id, message, int(sync_pending)),
    )
    conn.commit()


def fetch_recent_readings(conn: sqlite3.Connection, astronaut_id: str | None = None, limit: int = 500):
    if astronaut_id:
        rows = conn.execute(
            """
            SELECT astronaut_id, ts, signal, value, source, quality, sync_pending
            FROM readings
            WHERE astronaut_id = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (astronaut_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT astronaut_id, ts, signal, value, source, quality, sync_pending
            FROM readings
            ORDER BY ts DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_events(conn: sqlite3.Connection, astronaut_id: str | None = None, limit: int = 500):
    if astronaut_id:
        rows = conn.execute(
            "SELECT astronaut_id, ts, kind FROM events WHERE astronaut_id = ? ORDER BY ts DESC LIMIT ?",
            (astronaut_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT astronaut_id, ts, kind FROM events ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_alerts(conn: sqlite3.Connection, astronaut_id: str | None = None):
    if astronaut_id:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE astronaut_id = ? ORDER BY ts DESC",
            (astronaut_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM alerts ORDER BY ts DESC").fetchall()
    return [dict(r) for r in rows]


def fetch_notifications(conn: sqlite3.Connection, astronaut_id: str | None = None):
    if astronaut_id:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE astronaut_id = ? ORDER BY ts DESC",
            (astronaut_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notifications ORDER BY ts DESC").fetchall()
    return [dict(r) for r in rows]


def count_rows(conn: sqlite3.Connection, table_name: str):
    row = conn.execute(f"SELECT COUNT(*) as c FROM {table_name}").fetchone()
    return int(row["c"]) if row else 0


def clear_tables(conn, tables: Iterable[str]):
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


if __name__ == "__main__":
    conn = connect_db()
    init_db(conn)
    print("DB ready.")
