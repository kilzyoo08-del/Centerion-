"""Durable SQLite storage for conversation history and user facts."""
from __future__ import annotations
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

_DB_PATH = Path(os.getenv("CENTERION_DB_PATH", "./data/centerion.sqlite3"))
_LOCK = threading.RLock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize() -> None:
    with _LOCK, _connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('user','assistant')),
          content TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id,id);
        CREATE TABLE IF NOT EXISTS facts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id TEXT NOT NULL,
          fact TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(user_id,fact)
        );
        CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id,id);
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          core TEXT NOT NULL,
          status TEXT NOT NULL,
          input_json TEXT NOT NULL,
          output_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)


def add_message(user_id: str, role: str, content: str) -> None:
    with _LOCK, _connect() as db:
        db.execute("INSERT INTO messages(user_id,role,content) VALUES(?,?,?)", (user_id, role, content))


def get_history(user_id: str, limit: int = 12) -> list[dict[str, str]]:
    with _LOCK, _connect() as db:
        rows = db.execute("SELECT role,content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def remember_fact(user_id: str, fact: str) -> None:
    fact = fact.strip()[:2000]
    if not fact:
        return
    with _LOCK, _connect() as db:
        db.execute("INSERT OR IGNORE INTO facts(user_id,fact) VALUES(?,?)", (user_id, fact))


def get_facts(user_id: str, limit: int = 50) -> list[str]:
    with _LOCK, _connect() as db:
        rows = db.execute("SELECT fact FROM facts WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    return [r["fact"] for r in rows]


def save_job(job_id: str, user_id: str, core: str, status: str, input_data: dict[str, Any], output_data: dict[str, Any] | None = None) -> None:
    with _LOCK, _connect() as db:
        db.execute("""INSERT INTO jobs(id,user_id,core,status,input_json,output_json)
          VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,
          output_json=excluded.output_json,updated_at=CURRENT_TIMESTAMP""",
          (job_id,user_id,core,status,json.dumps(input_data,ensure_ascii=False),
           json.dumps(output_data,ensure_ascii=False) if output_data is not None else None))
