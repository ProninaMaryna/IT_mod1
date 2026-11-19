"""Доступ до SQLite: схема та репозиторії користувачів і файлів."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from ..core.models import FileRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    size        INTEGER NOT NULL,
    sha256      TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    edited_by   TEXT NOT NULL,
    UNIQUE (owner_id, name)
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class Database:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self.lock = threading.RLock()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self._conn.execute(sql, params).fetchall()


class UserRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, username: str, password_hash: str) -> int:
        cur = self.db.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, utcnow().isoformat()),
        )
        return int(cur.lastrowid)

    def by_username(self, username: str) -> sqlite3.Row | None:
        rows = self.db.query("SELECT * FROM users WHERE username = ?", (username,))
        return rows[0] if rows else None

    def by_id(self, user_id: int) -> sqlite3.Row | None:
        rows = self.db.query("SELECT * FROM users WHERE id = ?", (user_id,))
        return rows[0] if rows else None


def row_to_record(row: sqlite3.Row) -> FileRecord:
    return FileRecord(
        id=row["id"],
        name=row["name"],
        size=row["size"],
        sha256=row["sha256"],
        created_at=datetime.fromisoformat(row["created_at"]),
        modified_at=datetime.fromisoformat(row["modified_at"]),
        uploaded_by=row["uploaded_by"],
        edited_by=row["edited_by"],
    )


class FileRepo:
    def __init__(self, db: Database):
        self.db = db

    def list(self, owner_id: int) -> list[sqlite3.Row]:
        return self.db.query("SELECT * FROM files WHERE owner_id = ? ORDER BY id", (owner_id,))

    def get(self, owner_id: int, file_id: int) -> sqlite3.Row | None:
        rows = self.db.query("SELECT * FROM files WHERE owner_id = ? AND id = ?", (owner_id, file_id))
        return rows[0] if rows else None

    def by_name(self, owner_id: int, name: str) -> sqlite3.Row | None:
        rows = self.db.query("SELECT * FROM files WHERE owner_id = ? AND name = ?", (owner_id, name))
        return rows[0] if rows else None

    def insert(self, owner_id: int, name: str, size: int, sha: str, key: str, user: str, now: datetime) -> int:
        cur = self.db.execute(
            "INSERT INTO files (owner_id, name, size, sha256, storage_key, created_at, modified_at,"
            " uploaded_by, edited_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (owner_id, name, size, sha, key, now.isoformat(), now.isoformat(), user, user),
        )
        return int(cur.lastrowid)

    def update_content(self, file_id: int, size: int, sha: str, key: str, user: str, now: datetime) -> None:
        self.db.execute(
            "UPDATE files SET size = ?, sha256 = ?, storage_key = ?, modified_at = ?, edited_by = ? WHERE id = ?",
            (size, sha, key, now.isoformat(), user, file_id),
        )

    def delete(self, file_id: int) -> None:
        self.db.execute("DELETE FROM files WHERE id = ?", (file_id,))
