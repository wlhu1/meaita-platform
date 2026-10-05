# -*- coding: utf-8 -*-
"""最终验证测试"""
import urllib.request
import json
import time

BASE = "http://127.0.0.1:8000"

def post(url, data, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

# 重置
post(f"{BASE}/api/demo/reset", {})

# 测试学生聊天
print("=== 学生聊天测试 ===")
start = time.time()
r = post(f"{BASE}/api/agent/chat", {
    "role": "student",
    "user_id": "student001",
    "message": "这道假设检验题怎么做？",
    "current_knowledge_node": "t_test"
})
elapsed = time.time() - start

print(f"响应时间: {elapsed:.1f}秒")
print(f"phase: {r['phase']}")
print(f"generation_source: {r.get('generation_source', 'unknown')}")
print(f"Help Level: L{r['help_level']}")
print(f"Agent数: {len(r['active_agents'])}")
print(f"回复前150字:")
print(r['answer'][:150])
