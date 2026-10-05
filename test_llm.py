# -*- coding: utf-8 -*-
"""测试智谱LLM调用"""
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=" * 60)
print("测试1：教师AI班级分析（接智谱）")
print("=" * 60)
r = post(f"{BASE}/api/agent/chat", {
    "role": "teacher",
    "user_id": "teacher001",
    "message": "分析一下这个班假设检验掌握情况"
})
print(f"Intent: {r['intent']}")
print(f"Agents: {len(r['active_agents'])}个")
for a in r["active_agents"]:
    print(f"  - {a['name']}: {a['task']}")
print(f"\n回答前200字:")
print(r["answer"][:200])

print("\n" + "=" * 60)
print("测试2：AI教学设计（接智谱）")
print("=" * 60)
r2 = post(f"{BASE}/api/teacher/design", {"topic": "中心极限定理"})
print(f"设计前200字:")
print(r2["design"][:200])

print("\n" + "=" * 60)
print("测试3：练习生成（接智谱）")
print("=" * 60)
r3 = post(f"{BASE}/api/teacher/assessment", {"topic": "t检验"})
print(f"练习前200字:")
print(r3["assessment"][:200])
