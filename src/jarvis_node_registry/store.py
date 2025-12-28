from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

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
    _conn: sqlite3.Connection = field(init=False)

    def __post_init__(self) -> None:
        self._path = _sqlite_path_from_url(self.db_url)
        if self._path != ":memory:":
            _ensure_parent_dir(self._path)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
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
        self._conn.commit()

    def publish(self, node_type: NodeType) -> NodeType:
        payload = node_type.model_dump(exclude_none=True)
        cur = self._conn.cursor()
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
        self._conn.commit()
        return node_type

    def get(self, node_type_id: str, version: str) -> NodeType | None:
        cur = self._conn.cursor()
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
        cur = self._conn.cursor()
        cur.execute(query, params)
        return [NodeType.model_validate_json(row["node_type_json"]) for row in cur.fetchall()]

    def list_versions(self, node_type_id: str) -> Iterable[str]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT version FROM node_types WHERE node_type_id=?",
            (node_type_id,),
        )
        return [row["version"] for row in cur.fetchall()]
