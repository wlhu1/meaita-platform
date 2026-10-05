# -*- coding: utf-8 -*-
"""多智能体系统测试脚本"""
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

def test_chat(message, label, expected_phase=None):
    data = post(f"{BASE}/api/agent/chat", {
        "role": "student",
        "user_id": "student001",
        "message": message
    })
    print(f"=== {label} ===")
    print(f"Phase: {data['phase']} (预期: {expected_phase})")
    print(f"Intent: {data['intent']}")
    print(f"Help Level: L{data['help_level']}")
    print(f"Agents: {len(data['active_agents'])}个")
    for a in data["active_agents"]:
        print(f"  - {a['name']}: {a['task']}")
    if data["knowledge_updates"]:
        ku = data["knowledge_updates"][0]
        print(f"知识更新: {ku['node']} mastery {ku['mastery_before']:.2f} → {ku['mastery_after']:.2f}")
    print()
    return data

# 测试1：课前
d1 = test_chat("我明天要开始学习假设检验，应该先复习什么？", "测试1：课前预习", "PRE_CLASS")

# 测试2：课中
d2 = test_chat("为什么总体方差未知的时候通常不能直接用Z检验？", "测试2：课中提问", "IN_CLASS")

# 测试3：Help Ladder递增
print("=== 测试3：Help Ladder递增 ===")
for i in range(3):
    d = post(f"{BASE}/api/agent/chat", {
        "role": "student",
        "user_id": "student001",
        "message": "我还是不会做"
    })
    print(f"  第{i+1}轮: Help Level = L{d['help_level']}")
print()

# 测试4：课后总结
d4 = test_chat("总结一下我今天假设检验还有哪些地方没掌握。", "测试4：课后总结", "POST_CLASS")

# 测试5：教师Dashboard真实数据
print("=== 测试5：教师Dashboard ===")
dash = get(f"{BASE}/api/teacher/dashboard")
print(f"平均掌握度: {dash['avg_mastery']:.0%}")
print(f"数据来源: {dash.get('data_source', '未知')}")
print(f"薄弱TOP1: {dash['weak_topics'][0]['name']} ({dash['weak_topics'][0]['mastery']:.0%})")
print()

# 测试6：知识图谱读取真实数据
print("=== 测试6：学生知识图谱 ===")
graph = get(f"{BASE}/api/student/student001/knowledge-graph")
print(f"节点数: {len(graph['nodes'])}")
print(f"数据来源: {graph.get('data_source', '未知')}")
t_test = [n for n in graph['nodes'] if n['id'] == 't_test'][0]
print(f"t检验掌握度: {t_test['mastery']:.2f} (状态: {t_test['status']})")

