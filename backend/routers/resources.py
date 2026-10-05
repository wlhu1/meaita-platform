# -*- coding: utf-8 -*-
"""ME-AITA 优质资源推荐 API

本地资源库：真实资源以 JSON 形式存放于 data/resources.json 与 SQLite，
支持按学段 / 学科 / 类别检索与批量导入。禁止伪造资源。
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import DATA_DIR, RESOURCES_JSON
from database import get_db

router = APIRouter(prefix="/api/resources", tags=["resources"])

CATEGORIES = [
    "课程标准",
    "数字素养学习材料",
    "教学设计案例",
    "课堂教学资源",
    "教研资料",
    "AI教学工具使用指南",
]


class ResourceItem(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(default="", max_length=200)
    stage: str = Field(default="通用", max_length=50)
    subject: str = Field(default="通用", max_length=50)
    category: str = Field(min_length=1, max_length=50)
    content: str = Field(default="", max_length=2000)
    url: str = Field(default="", max_length=500)


class ResourceImport(BaseModel):
    resources: list[ResourceItem] = Field(min_length=1)


def _ensure_seed() -> None:
    """首次启动时把 data/resources.json 种子数据导入 SQLite。"""
    db = get_db()
    if db.list_resources():
        return
    if RESOURCES_JSON.is_file():
        try:
            items = json.loads(RESOURCES_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            items = []
        for item in items:
            if item.get("name"):
                db.add_resource(item)


@router.get("/categories")
def get_categories():
    return {"categories": CATEGORIES}


@router.get("")
def list_resources(stage: str = "全部", subject: str = "全部", category: str = "全部", q: str = ""):
    _ensure_seed()
    items = get_db().list_resources(
        stage=stage or "全部",
        subject=subject or "全部",
        category=category or "全部",
        q=(q or "").strip() or None,
    )
    return {
        "total": len(items),
        "categories": CATEGORIES,
        "resources": items,
    }


@router.post("/import")
def import_resources(body: ResourceImport):
    """批量导入真实资源（供管理端或后续资源维护使用）。"""
    db = get_db()
    added = 0
    for item in body.resources:
        if item.category not in CATEGORIES:
            raise HTTPException(status_code=400, detail=f"类别 {item.category} 不在允许列表中")
        db.add_resource(item.model_dump())
        added += 1
    return {"ok": True, "added": added}


@router.get("/seed/status")
def seed_status():
    """检查种子资源是否已导入（开发/运维用）。"""
    _ensure_seed()
    return {"seeded": True, "count": len(get_db().list_resources())}
