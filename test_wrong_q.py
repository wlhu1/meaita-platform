# -*- coding: utf-8 -*-
"""测试错题自动入库和错因聚合"""
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get(url):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))

# 学生答错
r = post(f"{BASE}/api/agent/chat", {
    "role": "student", "user_id": "student001",
    "message": "方差未知用Z检验",
    "current_knowledge_node": "t_test"
})
print("Evaluation:", r["evaluation"]["correctness"])
print("错题自动入库:", r["wrong_question_added"])

# 查错因聚合
misc = get(f"{BASE}/api/teacher/misconceptions")
print(f"\n高频错因数: {len(misc['misconceptions'])}")
for m in misc["misconceptions"]:
    print(f"  - {m['error_type']}: {m['total_count']}次, {m['student_count']}名学生, 知识点={m['node_id']}")

# 查学生错题本
wb = get(f"{BASE}/api/student/student001/wrong-book")
print(f"\n学生错题数: {wb['total']}")
for w in wb["wrong_questions"][:3]:
    print(f"  - [{w.get('error_type','')}] {w['question'][:30]}... status={w['status']}")
