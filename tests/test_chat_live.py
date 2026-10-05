# -*- coding: utf-8 -*-
"""真实联调测试：连接运行中的后端，执行一次真实问答与一次连续追问。

前置条件：已启动后端（venv\\Scripts\\python.exe backend\\main.py 或 启动智能体.bat）
运行：venv\\Scripts\\python.exe tests\\test_chat_live.py
"""
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8000"


def stream_chat(client: httpx.Client, session_id, message, search=False):
    """调用 SSE 流式接口并聚合返回内容。"""
    with client.stream(
        "POST", BASE + "/api/chat/stream",
        json={"session_id": session_id, "message": message, "search": search},
        timeout=180,
    ) as resp:
        resp.raise_for_status()
        full = ""
        events = {"delta": 0, "error": None, "meta": None, "done": None}
        for line in resp.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = json.loads(line[5:].strip())
            if payload["type"] == "delta":
                full += payload["content"]
                events["delta"] += 1
            elif payload["type"] == "meta":
                events["meta"] = payload["session_id"]
            elif payload["type"] == "done":
                events["done"] = payload["content"]
            elif payload["type"] == "error":
                events["error"] = payload["message"]
        return full, events


def main() -> None:
    print("=" * 64)
    print("ME-AITA 真实联调测试（智谱大模型）")
    print("=" * 64)

    with httpx.Client() as client:
        # 0. 健康检查
        info = client.get(BASE + "/api/info").json()
        print(f"[0] 后端信息: 模型={info['model']} Key已配置={info['api_configured']}")

        # 1. 新建会话
        r = client.post(BASE + "/api/sessions", json={"title": "联调测试会话"})
        sid = r.json()["session"]["id"]
        print(f"[1] 已创建会话 id={sid}")

        # 2. 第一轮：真实问答
        print("[2] 第一轮提问：帮我设计一节初中数学二次函数课程（仅需给出课题与目标框架）")
        t0 = time.time()
        full1, ev1 = stream_chat(client, sid, "帮我设计一节初中数学二次函数课程。请先给出课题、课时和教学目标框架，简洁作答。")
        cost = time.time() - t0
        assert ev1["error"] is None, f"第一轮出错: {ev1['error']}"
        assert len(full1) > 20, "第一轮返回过短"
        print(f"    → 返回 {len(full1)} 字, 流式片段 {ev1['delta']} 个, 耗时 {cost:.1f}s")
        print("    内容预览:", full1[:120].replace("\n", " "), "…")

        # 3. 第二轮：连续追问（验证上下文）
        print("[3] 第二轮追问：请优化其中的课堂互动环节（验证多轮上下文）")
        t0 = time.time()
        full2, ev2 = stream_chat(client, sid, "请针对上面方案中的课堂互动环节给出更具体的优化建议，简洁作答。")
        cost = time.time() - t0
        assert ev2["error"] is None, f"第二轮出错: {ev2['error']}"
        assert len(full2) > 20, "第二轮返回过短"
        print(f"    → 返回 {len(full2)} 字, 流式片段 {ev2['delta']} 个, 耗时 {cost:.1f}s")
        print("    内容预览:", full2[:120].replace("\n", " "), "…")

        # 4. 验证历史消息已持久化
        msgs = client.get(f"{BASE}/api/sessions/{sid}/messages").json()["messages"]
        roles = [m["role"] for m in msgs]
        print(f"[4] 会话历史消息 {len(msgs)} 条: {roles}")
        assert roles.count("user") == 2 and roles.count("assistant") == 2

        # 5. 删除测试会话
        client.delete(f"{BASE}/api/sessions/{sid}")
        print("[5] 已清理测试会话")

    print("=" * 64)
    print("联调测试全部通过 ✓（真实智谱模型返回）")
    print("=" * 64)


if __name__ == "__main__":
    main()
