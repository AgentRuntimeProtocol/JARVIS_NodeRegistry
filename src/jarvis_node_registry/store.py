from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from arp_standard_model import NodeKind, NodeType


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sqlite_path_from_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///") :]
    if url.startswith("sqlite://"):
        return url[len("sqlite://") :]
    return url


def _ensure_parent_dir(path: str) -> None:
    parent = Path(path).expanduser().resolve().parent
    os.makedirs(parent, exist_ok=True)


@dataclass(slots=True)
class NodeTypeStore:
    db_url: str
    _path: str = field(init=False)
    _is_memory: bool = field(init=False)
    _busy_timeout_ms: int = field(default=5000, init=False)
    _keepalive: sqlite3.Connection | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._path = _sqlite_path_from_url(self.db_url)
        self._is_memory = self._path == ":memory:"
        if not self._is_memory:
            _ensure_parent_dir(self._path)
        else:
            self._keepalive = self._open_connection()
        self._init_schema()

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if not self._is_memory:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
        return conn

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._is_memory:
            if self._keepalive is None:
                self._keepalive = self._open_connection()
            yield self._keepalive
            return
        conn = self._open_connection()
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS node_types (
                  node_type_id TEXT NOT NULL,
                  version TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  node_type_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  PRIMARY KEY (node_type_id, version)
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_node_types_id ON node_types(node_type_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_node_types_kind ON node_types(kind)"
            )
            conn.commit()

    def publish(self, node_type: NodeType) -> NodeType:
        payload = node_type.model_dump(exclude_none=True)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO node_types (node_type_id, version, kind, node_type_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    node_type.node_type_id,
                    node_type.version,
                    node_type.kind.value,
                    json.dumps(payload, separators=(",", ":")),
                    _now_iso(),
                ),
            )
            conn.commit()
        return node_type

    def upsert(self, node_type: NodeType) -> NodeType:
        payload = node_type.model_dump(exclude_none=True)
        node_type_json = json.dumps(payload, separators=(",", ":"))
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO node_types (node_type_id, version, kind, node_type_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(node_type_id, version) DO UPDATE SET
                  kind=excluded.kind,
                  node_type_json=excluded.node_type_json
                """,
                (
                    node_type.node_type_id,
                    node_type.version,
                    node_type.kind.value,
                    node_type_json,
                    _now_iso(),
                ),
            )
            conn.commit()
        return node_type

    def get(self, node_type_id: str, version: str) -> NodeType | None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT node_type_json FROM node_types WHERE node_type_id=? AND version=?",
                (node_type_id, version),
            )
            if (row := cur.fetchone()) is None:
                return None
            return NodeType.model_validate_json(row["node_type_json"])

    def list(self, *, q: str | None, kind: NodeKind | None) -> list[NodeType]:
        q = (q or "").strip().lower()
        query = "SELECT node_type_json FROM node_types"
        clauses: list[str] = []
        params: list[str] = []
        if q:
            clauses.append("LOWER(node_type_id) LIKE ?")
            params.append(f"%{q}%")
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind.value)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY node_type_id, version"
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return [NodeType.model_validate_json(row["node_type_json"]) for row in cur.fetchall()]

    def list_versions(self, node_type_id: str) -> Iterable[str]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT version FROM node_types WHERE node_type_id=?",
                (node_type_id,),
            )
            return [row["version"] for row in cur.fetchall()]
