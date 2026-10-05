# -*- coding: utf-8 -*-
"""ME-AITA 聊天与会话管理 API"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import get_model
from database import get_db
from prompts import SYSTEM_PROMPT
from zhipu_client import ZhipuClient, ZhipuError

logger = logging.getLogger("meaita.chat")
router = APIRouter(prefix="/api", tags=["chat"])

# 单次请求携带的历史消息条数上限（含上下文窗口控制）
MAX_CONTEXT_MESSAGES = 24
# 单条消息送入模型的最大字符数（防止超长输入）
MAX_MESSAGE_CHARS = 12000

WEB_SEARCH_TOOL = {
    "type": "web_search",
    "web_search": {"search_query": "", "search_result": True},
}


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=60)


class SessionRename(BaseModel):
    title: str = Field(max_length=60)


class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str = Field(default="", max_length=MAX_MESSAGE_CHARS)
    search: bool = False


def _sse(event: str, data: dict) -> str:
    payload = dict(data)
    payload.setdefault("type", event)
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ---------- 会话管理 ----------
@router.get("/sessions")
def list_sessions():
    return {"sessions": get_db().list_sessions()}


@router.post("/sessions")
def create_session(body: SessionCreate):
    session = get_db().create_session(title=body.title)
    return {"session": session}


@router.post("/sessions/{session_id}/rename")
def rename_session(session_id: int, body: SessionRename):
    session = get_db().rename_session(session_id, body.title)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session": session}


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: int):
    if not get_db().get_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"messages": get_db().list_messages(session_id)}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int):
    ok = get_db().delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}


# ---------- 流式问答 ----------
@router.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    db = get_db()
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 确定会话
    session_id = body.session_id
    if session_id is None:
        session = db.create_session(title=message[:20])
        session_id = session["id"]
    else:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

    # 保存用户消息
    db.add_message(session_id, "user", message)

    def _build_messages() -> list[dict]:
        history = db.list_messages(session_id, limit=MAX_CONTEXT_MESSAGES)
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in history:
            role = "assistant" if item["role"] == "assistant" else "user"
            content = item["content"]
            if len(content) > MAX_MESSAGE_CHARS:
                content = content[:MAX_MESSAGE_CHARS] + "…（内容过长已截断）"
            messages.append({"role": role, "content": content})
        return messages

    def _event_stream():
        client = ZhipuClient(model=get_model())
        tools = [dict(WEB_SEARCH_TOOL)] if body.search else None
        full_text: list[str] = []
        try:
            yield _sse("meta", {"session_id": session_id})
            for piece in client.chat_stream(_build_messages(), tools=tools):
                if not piece:
                    continue
                full_text.append(piece)
                yield _sse("delta", {"content": piece})
            answer = "".join(full_text).strip()
            if not answer:
                raise ZhipuError("unknown", "模型返回内容为空，请重试。")
            db.add_message(session_id, "assistant", answer)
            yield _sse("done", {"session_id": session_id, "content": answer})
        except ZhipuError as exc:
            logger.error("会话 %s 调用智谱失败: %s", session_id, exc.code)
            yield _sse("error", {"code": exc.code, "message": exc.message})
        except Exception as exc:  # noqa: BLE001
            logger.exception("会话 %s 未知异常", session_id)
            yield _sse("error", {"code": "unknown", "message": "服务内部异常，请稍后重试。"})

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ME-AITA 教师成长智能体",
        "model": get_model(),
    }
