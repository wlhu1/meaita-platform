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
CREATE TABLE IF NOT EXISTS community_posts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- ===== 多智能体智慧教学平台新增表 =====
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT DEFAULT '',
    is_demo INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS classes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    teacher_id INTEGER NOT NULL,
    is_demo INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS class_members(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(class_id) REFERENCES classes(id),
    FOREIGN KEY(student_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS knowledge_nodes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    name TEXT NOT NULL,
    chapter TEXT NOT NULL,
    description TEXT DEFAULT '',
    bloom_level INTEGER DEFAULT 1,
    common_misconception TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(course_id, node_id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS knowledge_edges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    relation TEXT DEFAULT 'prerequisite',
    created_at TEXT NOT NULL,
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS learner_states(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    mastery REAL DEFAULT 0.0,
    bloom_level INTEGER DEFAULT 1,
    error_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'unlearned',
    last_updated TEXT NOT NULL,
    UNIQUE(user_id, course_id, node_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS practice_records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    question TEXT NOT NULL,
    user_answer TEXT DEFAULT '',
    correct_answer TEXT DEFAULT '',
    is_correct INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS wrong_questions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    question TEXT NOT NULL,
    user_answer TEXT DEFAULT '',
    correct_answer TEXT DEFAULT '',
    misconception TEXT DEFAULT '',
    status TEXT DEFAULT 'open',
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS learning_paths(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS agent_runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    session_id INTEGER,
    agent_name TEXT NOT NULL,
    task TEXT DEFAULT '',
    phase TEXT DEFAULT 'GENERAL',
    intent TEXT DEFAULT '',
    status TEXT DEFAULT 'done',
    confidence REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
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
            # ===== 数据库迁移：为旧表补充新字段 =====
            self._migrate_columns(conn)
            conn.commit()
        finally:
            conn.close()

    def _migrate_columns(self, conn):
        """为已有表补充新增字段（SQLite不支持ALTER ADD COLUMN IF NOT EXISTS，需手动检查）"""
        # wrong_questions 新增字段
        existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(wrong_questions)").fetchall()]
        new_cols = {
            "question_hash": "TEXT DEFAULT ''",
            "error_type": "TEXT DEFAULT ''",
            "help_level": "INTEGER DEFAULT 2",
            "error_count": "INTEGER DEFAULT 1",
            "last_wrong_at": "TEXT",
            "corrected_at": "TEXT",
            "final_score": "REAL",
        }
        for col, col_type in new_cols.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE wrong_questions ADD COLUMN {col} {col_type}")

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

    # ---------- 教师社区 ----------
    def add_post(self, author: str, title: str, body: str) -> int:
        conn = self.connect()
        try:
            cur = conn.execute(
                "INSERT INTO community_posts(author, title, body, created_at) VALUES(?,?,?,?)",
                (author.strip() or "匿名教师", title.strip(), body.strip(), _now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def list_posts(self, limit: int = 100) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT id, author, title, body, created_at FROM community_posts ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_post(self, post_id: int) -> bool:
        conn = self.connect()
        try:
            cur = conn.execute("DELETE FROM community_posts WHERE id=?", (post_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    # ===== 多智能体平台数据初始化与查询 =====
    def init_demo_data(self) -> None:
        """初始化演示课程：概率论与数理统计"""
        conn = self.connect()
        try:
            # 检查是否已有演示课程
            existing = conn.execute("SELECT id FROM courses WHERE name=?", ("概率论与数理统计",)).fetchone()
            if existing:
                return
            now = _now()

            # 用户：1教师 + 5学生
            users = [
                ("teacher001", "王老师", "teacher"),
                ("student001", "张三", "student"),
                ("student002", "李四", "student"),
                ("student003", "王五", "student"),
                ("student004", "赵六", "student"),
                ("student005", "钱七", "student"),
            ]
            for u in users:
                conn.execute(
                    "INSERT OR IGNORE INTO users(username, display_name, role, created_at) VALUES(?,?,?,?)",
                    (*u, now),
                )

            # 课程
            cur = conn.execute(
                "INSERT INTO courses(name, subject, description, is_demo, created_at) VALUES(?,?,?,?,?)",
                ("概率论与数理统计", "数学", "演示课程：概率论与数理统计", 1, now),
            )
            course_id = cur.lastrowid

            # 班级
            teacher = conn.execute("SELECT id FROM users WHERE username='teacher001'").fetchone()
            conn.execute(
                "INSERT INTO classes(course_id, name, teacher_id, is_demo, created_at) VALUES(?,?,?,?,?)",
                (course_id, "2024级应用统计1班（演示）", teacher["id"], 1, now),
            )
            class_row = conn.execute("SELECT id FROM classes WHERE course_id=?", (course_id,)).fetchone()

            # 学生加入班级
            students = conn.execute("SELECT id FROM users WHERE role='student'").fetchall()
            for s in students:
                conn.execute(
                    "INSERT INTO class_members(class_id, student_id, created_at) VALUES(?,?,?)",
                    (class_row["id"], s["id"], now),
                )

            # 知识节点（概率论与数理统计）
            nodes = [
                ("probability", "概率论基础", "概率论", "随机事件与概率基本概念", 1),
                ("conditional_prob", "条件概率", "概率论", "条件概率与乘法公式", 2),
                ("random_var", "随机变量", "概率论", "随机变量及其分布", 2),
                ("discrete_dist", "离散型分布", "概率论", "二项分布、泊松分布", 2),
                ("continuous_dist", "连续型分布", "概率论", "正态分布、均匀分布", 2),
                ("expectation", "数学期望", "概率论", "期望的定义与性质", 2),
                ("variance", "方差", "概率论", "方差与协方差", 2),
                ("lln", "大数定律", "概率论", "大数定律", 3),
                ("clt", "中心极限定理", "概率论", "中心极限定理", 3),
                ("pop_sample", "总体与样本", "数理统计", "统计基本概念", 1),
                ("point_est", "点估计", "数理统计", "矩估计与极大似然估计", 3),
                ("interval_est", "区间估计", "数理统计", "置信区间", 3),
                ("hypothesis_test", "假设检验", "数理统计", "假设检验基本思想", 3),
                ("z_test", "Z检验", "数理统计", "总体方差已知时的检验", 3),
                ("t_test", "t检验", "数理统计", "总体方差未知时的检验", 3),
                ("chi2_test", "卡方检验", "数理统计", "拟合优度检验", 3),
            ]
            for n in nodes:
                conn.execute(
                    "INSERT INTO knowledge_nodes(course_id, node_id, name, chapter, description, bloom_level, created_at) VALUES(?,?,?,?,?,?,?)",
                    (course_id, n[0], n[1], n[2], n[3], n[4], now),
                )

            # 知识边（前置关系）
            edges = [
                ("probability", "conditional_prob"),
                ("conditional_prob", "random_var"),
                ("random_var", "discrete_dist"),
                ("random_var", "continuous_dist"),
                ("discrete_dist", "expectation"),
                ("continuous_dist", "expectation"),
                ("expectation", "variance"),
                ("variance", "lln"),
                ("lln", "clt"),
                ("clt", "pop_sample"),
                ("pop_sample", "point_est"),
                ("point_est", "interval_est"),
                ("interval_est", "hypothesis_test"),
                ("hypothesis_test", "z_test"),
                ("hypothesis_test", "t_test"),
                ("hypothesis_test", "chi2_test"),
            ]
            for e in edges:
                conn.execute(
                    "INSERT INTO knowledge_edges(course_id, from_node, to_node, relation, created_at) VALUES(?,?,?,?,?)",
                    (course_id, e[0], e[1], "prerequisite", now),
                )

            # 学生学习状态（演示数据）
            student_ids = [s["id"] for s in students]
            # 张三：学到t检验，掌握度不均
            demo_states = [
                # (user_idx, node_id, mastery, status)
                (0, "probability", 0.9, "mastered"),
                (0, "conditional_prob", 0.85, "mastered"),
                (0, "random_var", 0.8, "mastered"),
                (0, "discrete_dist", 0.75, "mastered"),
                (0, "continuous_dist", 0.7, "mastered"),
                (0, "expectation", 0.65, "learning"),
                (0, "variance", 0.5, "learning"),
                (0, "lln", 0.3, "weak"),
                (0, "clt", 0.2, "weak"),
                (0, "pop_sample", 0.4, "learning"),
                (0, "point_est", 0.3, "weak"),
                (0, "interval_est", 0.2, "weak"),
                (0, "hypothesis_test", 0.35, "learning"),
                (0, "z_test", 0.4, "learning"),
                (0, "t_test", 0.25, "weak"),
                (0, "chi2_test", 0.0, "unlearned"),
                # 李四：稍弱
                (1, "probability", 0.8, "mastered"),
                (1, "conditional_prob", 0.7, "mastered"),
                (1, "random_var", 0.6, "learning"),
                (1, "discrete_dist", 0.5, "learning"),
                (1, "continuous_dist", 0.4, "weak"),
                (1, "expectation", 0.3, "weak"),
                (1, "variance", 0.2, "weak"),
                (1, "lln", 0.0, "unlearned"),
                (1, "clt", 0.0, "unlearned"),
                (1, "pop_sample", 0.0, "unlearned"),
                (1, "point_est", 0.0, "unlearned"),
                (1, "interval_est", 0.0, "unlearned"),
                (1, "hypothesis_test", 0.0, "unlearned"),
                (1, "z_test", 0.0, "unlearned"),
                (1, "t_test", 0.0, "unlearned"),
                (1, "chi2_test", 0.0, "unlearned"),
            ]
            for ds in demo_states:
                uid = student_ids[ds[0]]
                conn.execute(
                    "INSERT OR IGNORE INTO learner_states(user_id, course_id, node_id, mastery, bloom_level, error_count, status, last_updated) VALUES(?,?,?,?,?,?,?,?)",
                    (uid, course_id, ds[1], ds[2], 2, max(0, int(5 - ds[2]*5)), ds[3], now),
                )

            # 学习路径（张三）
            path = [
                ("probability", 1, "completed"),
                ("conditional_prob", 2, "completed"),
                ("random_var", 3, "completed"),
                ("expectation", 4, "completed"),
                ("variance", 5, "current"),
                ("lln", 6, "pending"),
                ("clt", 7, "pending"),
                ("hypothesis_test", 8, "pending"),
                ("t_test", 9, "pending"),
            ]
            for p in path:
                conn.execute(
                    "INSERT INTO learning_paths(user_id, course_id, node_id, sort_order, status, created_at) VALUES(?,?,?,?,?,?)",
                    (student_ids[0], course_id, p[0], p[1], p[2], now),
                )

            # 错题演示（张三）
            wrongs = [
                ("t_test", "某工厂生产的零件直径服从正态分布，标准差未知，抽取16个零件测得均值为20.5mm，样本标准差为2mm，问是否符合20mm的标准？",
                 "用Z检验", "用t检验，因为总体标准差未知", "Z检验与t检验适用条件混淆"),
                ("hypothesis_test", "假设检验中，p值小于显著性水平α时，应该？",
                 "接受原假设", "拒绝原假设", "p值决策方向错误"),
            ]
            for w in wrongs:
                conn.execute(
                    "INSERT INTO wrong_questions(user_id, course_id, node_id, question, user_answer, correct_answer, misconception, status, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (student_ids[0], course_id, w[0], w[1], w[2], w[3], w[4], "open", now),
                )

            conn.commit()
        finally:
            conn.close()

    def get_course_id_by_name(self, name: str) -> int | None:
        conn = self.connect()
        try:
            row = conn.execute("SELECT id FROM courses WHERE name=?", (name,)).fetchone()
            return row["id"] if row else None
        finally:
            conn.close()

    def list_knowledge_nodes(self, course_id: int) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM knowledge_nodes WHERE course_id=? ORDER BY id", (course_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_knowledge_edges(self, course_id: int) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM knowledge_edges WHERE course_id=?", (course_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_learner_state(self, user_id: int, course_id: int) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM learner_states WHERE user_id=? AND course_id=?", (user_id, course_id)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_learning_path(self, user_id: int, course_id: int) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM learning_paths WHERE user_id=? AND course_id=? ORDER BY sort_order",
                (user_id, course_id),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_wrong_questions(self, user_id: int, course_id: int) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM wrong_questions WHERE user_id=? AND course_id=? ORDER BY created_at DESC",
                (user_id, course_id),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> dict | None:
        conn = self.connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def log_agent_run(self, user_id: int | None, session_id: int | None,
                      agent_name: str, task: str, phase: str, intent: str,
                      status: str = "done", confidence: float = 0.0) -> int:
        conn = self.connect()
        try:
            cur = conn.execute(
                "INSERT INTO agent_runs(user_id, session_id, agent_name, task, phase, intent, status, confidence, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (user_id, session_id, agent_name, task, phase, intent, status, confidence, _now()),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def update_learner_state(self, user_id: int, course_id: int, node_id: str,
                             mastery_delta: float = 0.0, error_inc: int = 0,
                             bloom_level: int | None = None) -> dict:
        """更新学生学习状态"""
        conn = self.connect()
        try:
            # 先查询当前状态
            row = conn.execute(
                "SELECT * FROM learner_states WHERE user_id=? AND course_id=? AND node_id=?",
                (user_id, course_id, node_id),
            ).fetchone()

            if row:
                current = dict(row)
                new_mastery = max(0.0, min(1.0, current["mastery"] + mastery_delta))
                new_error = current["error_count"] + error_inc
                new_bloom = bloom_level if bloom_level else current["bloom_level"]

                # 自动更新状态
                if new_mastery >= 0.8:
                    new_status = "mastered"
                elif new_mastery >= 0.5:
                    new_status = "learning"
                elif new_mastery >= 0.2:
                    new_status = "weak"
                else:
                    new_status = "unlearned"

                conn.execute(
                    "UPDATE learner_states SET mastery=?, error_count=?, bloom_level=?, status=?, last_updated=? "
                    "WHERE user_id=? AND course_id=? AND node_id=?",
                    (new_mastery, new_error, new_bloom, new_status, _now(),
                     user_id, course_id, node_id),
                )
            else:
                # 新建记录
                new_mastery = max(0.0, min(1.0, mastery_delta if mastery_delta > 0 else 0.1))
                new_error = max(0, error_inc)
                new_status = "learning" if new_mastery > 0.2 else "unlearned"
                conn.execute(
                    "INSERT INTO learner_states(user_id, course_id, node_id, mastery, bloom_level, error_count, status, last_updated) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (user_id, course_id, node_id, new_mastery, bloom_level or 1, new_error, new_status, _now()),
                )

            conn.commit()
            return {
                "node_id": node_id,
                "mastery": new_mastery,
                "error_count": new_error,
                "status": new_status,
            }
        finally:
            conn.close()

    def add_wrong_question(self, user_id: int, course_id: int, node_id: str,
                           question: str, user_answer: str, correct_answer: str,
                           misconception: str = "", error_type: str = "",
                           help_level: int = 2) -> int:
        """新增错题（自动去重：同一用户同一知识点同一题目重复错误则更新次数）"""
        import hashlib
        q_hash = hashlib.md5(f"{node_id}:{question[:50]}".encode()).hexdigest()

        conn = self.connect()
        try:
            # 检查是否已有相同错题
            existing = conn.execute(
                "SELECT id, error_count FROM wrong_questions WHERE user_id=? AND node_id=? AND question_hash=? AND status='open'",
                (user_id, node_id, q_hash)
            ).fetchone()

            if existing:
                # 更新：增加错误次数，更新最新回答
                conn.execute(
                    "UPDATE wrong_questions SET user_answer=?, error_count=?, last_wrong_at=? WHERE id=?",
                    (user_answer, existing["error_count"] + 1, _now(), existing["id"])
                )
                conn.commit()
                return existing["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO wrong_questions(user_id, course_id, node_id, question, question_hash, "
                    "user_answer, correct_answer, misconception, error_type, help_level, error_count, status, created_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (user_id, course_id, node_id, question, q_hash,
                     user_answer, correct_answer, misconception, error_type, help_level, 1, "open", _now()),
                )
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def mark_wrong_question_corrected(self, wrong_id: int, final_score: float = 0.8) -> bool:
        """标记错题已订正"""
        conn = self.connect()
        try:
            conn.execute(
                "UPDATE wrong_questions SET status='corrected', corrected_at=?, final_score=? WHERE id=?",
                (_now(), final_score, wrong_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_class_misconceptions(self, course_id: int, limit: int = 10) -> list[dict]:
        """从wrong_questions实时聚合班级高频错因"""
        conn = self.connect()
        try:
            rows = conn.execute(
                """SELECT error_type, node_id, COUNT(*) as total_count,
                          COUNT(DISTINCT user_id) as student_count
                   FROM wrong_questions
                   WHERE course_id=? AND error_type IS NOT NULL AND error_type != ''
                   GROUP BY error_type, node_id
                   ORDER BY total_count DESC
                   LIMIT ?""",
                (course_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_class_avg_mastery(self, course_id: int) -> dict[str, float]:
        """计算班级各知识点平均掌握度"""
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT node_id, AVG(mastery) as avg_mastery, SUM(error_count) as total_errors "
                "FROM learner_states GROUP BY node_id"
            ).fetchall()
            return {r["node_id"]: {"mastery": r["avg_mastery"] or 0, "errors": r["total_errors"] or 0} for r in rows}
        finally:
            conn.close()


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        _db.init_demo_data()
    return _db
