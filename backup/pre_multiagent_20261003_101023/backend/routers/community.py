# -*- coding: utf-8 -*-
"""ME-AITA 教师社区（本地轻量教研讨论板）"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import get_db

router = APIRouter(prefix="/api/community", tags=["community"])


class PostCreate(BaseModel):
    author: str = Field(default="匿名教师", max_length=30)
    title: str = Field(..., min_length=2, max_length=80)
    body: str = Field(..., min_length=2, max_length=2000)


@router.get("/posts")
def list_posts(limit: int = 100):
    return {"posts": get_db().list_posts(limit=limit)}


@router.post("/posts")
def create_post(body: PostCreate):
    pid = get_db().add_post(author=body.author, title=body.title, body=body.body)
    return {"ok": True, "id": pid}


@router.delete("/posts/{post_id}")
def delete_post(post_id: int):
    ok = get_db().delete_post(post_id)
    if not ok:
        raise HTTPException(status_code=404, detail="帖子不存在或已删除")
    return {"ok": True}
