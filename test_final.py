# -*- coding: utf-8 -*-
"""封板前测试"""
import urllib.request
import json
import time

BASE = "http://127.0.0.1:8000"

def post(url, data, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

# 1. 重置
print("1. 重置演示数据...")
post(f"{BASE}/api/demo/reset", {})

# 2. 学生聊天测试（验证智谱调用）
print("\n2. 学生聊天测试（验证Socratic Tutor智谱调用）...")
start = time.time()
r = post(f"{BASE}/api/agent/chat", {
    "role": "student",
    "user_id": "student001",
    "message": "这道假设检验题怎么做？",
    "current_knowledge_node": "t_test"
}, timeout=60)
elapsed = time.time() - start

print(f"  响应时间: {elapsed:.1f}秒")
print(f"  generation_source: {r.get('generation_source', 'unknown')}")
print(f"  Help Level: L{r['help_level']}")
print(f"  Agent数: {len(r['active_agents'])}")
print(f"  回复前100字: {r['answer'][:100]}...")

# 3. 动态学习路径测试
print("\n3. 动态学习路径（前置关系）...")
path = get(f"{BASE}/api/student/student001/learning-path")
print(f"  数据来源: {path['data_source']}")
print(f"  前5个节点:")
for i, p in enumerate(path['path'][:5]):
    prereq_flag = " [需前置复习]" if p.get("needs_prereq") else ""
    print(f"    {i+1}. {p['name']} - mastery={p['mastery']:.2f} ({p['status']}){prereq_flag}")

# 4. E2E完整流程
print("\n4. 完整E2E闭环测试...")
tests = []

# 步骤1: 答错
r1 = post(f"{BASE}/api/agent/chat", {
    "role": "student", "user_id": "student001",
    "message": "方差未知用Z检验", "current_knowledge_node": "t_test"
})
tests.append(("答错→Evaluation", r1['evaluation']['correctness'] in ("incorrect", "partially_correct")))
tests.append(("错题自动入库", r1['wrong_question_added'] == True))

# 步骤2: 答对
r2 = post(f"{BASE}/api/agent/chat", {
    "role": "student", "user_id": "student001",
    "message": "总体方差未知应该用t分布", "current_knowledge_node": "t_test"
})
tests.append(("答对→mastery上升", r2['knowledge_updates'][0]['mastery_delta'] > 0))

# 步骤3: 教师Dashboard
dash = get(f"{BASE}/api/teacher/dashboard")
tests.append(("教师Dashboard真实聚合", dash['data_source'].startswith("learner_states")))

# 步骤4: 高频错因
misc = get(f"{BASE}/api/teacher/misconceptions")
tests.append(("高频错因DB聚合", misc['data_source'].startswith("wrong_questions")))

# 步骤5: AI知识图谱生成
kg = post(f"{BASE}/api/knowledge-graph/generate", {"topic": "正态总体均值的假设检验"}, timeout=60)
tests.append(("知识图谱生成", len(kg['nodes']) >= 8))

passed = sum(1 for _, ok in tests if ok)
print(f"  E2E测试: {passed}/{len(tests)} PASS")
for name, ok in tests:
    print(f"    {'✅' if ok else '❌'} {name}")
