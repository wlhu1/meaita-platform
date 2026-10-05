# -*- coding: utf-8 -*-
"""ME-AITA 教师成长智能体 - SQLite 数据层

保存会话、聊天消息、数字素养测评记录与本地资源库。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '新会话',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS diagnosis_records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identity TEXT NOT NULL,
    stage TEXT NOT NULL,
    subject TEXT NOT NULL,
    answers_json TEXT NOT NULL,
    scores_json TEXT NOT NULL,
    total_score INTEGER NOT NULL,
    level TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS resources(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source TEXT DEFAULT '',
    stage TEXT DEFAULT '通用',
    subject TEXT DEFAULT '通用',
    category TEXT NOT NULL,
    content TEXT DEFAULT '',
    url TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        conn = self.connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    # ---------- 会话 ----------
    def create_session(self, title: str | None = None) -> dict:
        now = _now()
        title = (title or "").strip() or "新会话"
        conn = self.connect()
        try:
            cur = conn.execute(
                "INSERT INTO sessions(title, created_at, updated_at) VALUES(?,?,?)",
                (title, now, now),
            )
            conn.commit()
            return self.get_session(cur.lastrowid)
        finally:
            conn.close()

    def list_sessions(self) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_session(self, session_id: int) -> dict | None:
        conn = self.connect()
        try:
            row = conn.execute(
                "SELECT id, title, created_at, updated_at FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def rename_session(self, session_id: int, title: str) -> dict | None:
        conn = self.connect()
        try:
            conn.execute(
                "UPDATE sessions SET title=?, updated_at=? WHERE id=?",
                (title.strip() or "新会话", _now(), session_id),
            )
            conn.commit()
            return self.get_session(session_id)
        finally:
            conn.close()

    def touch_session(self, session_id: int) -> None:
        conn = self.connect()
        try:
            conn.execute(
                "UPDATE sessions SET updated_at=? WHERE id=?", (_now(), session_id)
            )
            conn.commit()
        finally:
            conn.close()

    def delete_session(self, session_id: int) -> bool:
        conn = self.connect()
        try:
            cur = conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ---------- 消息 ----------
    def add_message(self, session_id: int, role: str, content: str) -> int:
        conn = self.connect()
        try:
            cur = conn.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
                (session_id, role, content, _now()),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=? WHERE id=?", (_now(), session_id)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def list_messages(self, session_id: int, limit: int | None = None) -> list[dict]:
        conn = self.connect()
        try:
            sql = (
                "SELECT id, role, content, created_at FROM messages "
                "WHERE session_id=? ORDER BY id ASC"
            )
            params: tuple[Any, ...] = (session_id,)
            if limit:
                rows = conn.execute(
                    "SELECT id, role, content, created_at FROM messages WHERE session_id=? "
                    "ORDER BY id DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
                rows = list(reversed(rows))
            else:
                rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---------- 数字素养测评 ----------
    def add_diagnosis(
        self,
        identity: str,
        stage: str,
        subject: str,
        answers: dict,
        scores: dict,
        total_score: int,
        level: str,
    ) -> int:
        conn = self.connect()
        try:
            cur = conn.execute(
                "INSERT INTO diagnosis_records(identity, stage, subject, answers_json, "
                "scores_json, total_score, level, created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    identity,
                    stage,
                    subject,
                    json.dumps(answers, ensure_ascii=False),
                    json.dumps(scores, ensure_ascii=False),
                    total_score,
                    level,
                    _now(),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def list_diagnosis(self, limit: int = 50) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM diagnosis_records ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["answers"] = json.loads(d.pop("answers_json"))
                d["scores"] = json.loads(d.pop("scores_json"))
                out.append(d)
            return out
        finally:
            conn.close()

    # ---------- 资源库 ----------
    def add_resource(self, item: dict) -> int:
        conn = self.connect()
        try:
            cur = conn.execute(
                "INSERT INTO resources(name, source, stage, subject, category, content, url, created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    item.get("name", "").strip(),
                    item.get("source", "").strip(),
                    item.get("stage", "通用").strip() or "通用",
                    item.get("subject", "通用").strip() or "通用",
                    item.get("category", "").strip(),
                    item.get("content", "").strip(),
                    item.get("url", "").strip(),
                    _now(),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def list_resources(
        self,
        stage: str | None = None,
        subject: str | None = None,
        category: str | None = None,
        q: str | None = None,
    ) -> list[dict]:
        conn = self.connect()
        try:
            sql = "SELECT * FROM resources WHERE 1=1"
            params: list[Any] = []
            if stage and stage != "全部":
                sql += " AND (stage=? OR stage='通用')"
                params.append(stage)
            if subject and subject != "全部":
                sql += " AND (subject=? OR subject='通用')"
                params.append(subject)
            if category and category != "全部":
                sql += " AND category=?"
                params.append(category)
            if q:
                sql += " AND (name LIKE ? OR content LIKE ? OR source LIKE ?)"
                like = f"%{q}%"
                params.extend([like, like, like])
            sql += " ORDER BY id ASC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
