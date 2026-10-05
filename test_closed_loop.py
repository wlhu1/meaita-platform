# -*- coding: utf-8 -*-
"""第三阶段闭环测试"""
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

print("=" * 60)
print("闭环测试1：学生答错 → Evaluation → 错题入库 → mastery下降")
print("=" * 60)

# 先记录初始状态
before = get(f"{BASE}/api/student/student001/knowledge-graph")
t_test_before = [n for n in before["nodes"] if n["id"] == "t_test"][0]
print(f"测试前 t检验 mastery: {t_test_before['mastery']:.2f}, errors: {t_test_before['error_count']}")

# 学生答错
r1 = post(f"{BASE}/api/agent/chat", {
    "role": "student", "user_id": "student001",
    "message": "方差未知的时候应该用Z检验",
    "current_knowledge_node": "t_test"
})
print(f"\n学生回答: '方差未知的时候应该用Z检验'")
print(f"Evaluation: {r1['evaluation']['correctness']} ({r1['evaluation']['error_type']})")
print(f"Feedback: {r1['evaluation']['feedback'][:60]}...")
print(f"Help Level: L{r1['help_level']}")
print(f"错题自动入库: {r1['wrong_question_added']}")
ku = r1["knowledge_updates"][0]
print(f"mastery变化: {ku['mastery_before']:.2f} → {ku['mastery_after']:.2f} (Δ={ku['mastery_delta']:+.3f})")
print(f"执行Agent: {len(r1['active_agents'])}个")
for a in r1["active_agents"]:
    print(f"  - {a['name']}: {a['task']}")

# 再看知识图谱是否同步
after = get(f"{BASE}/api/student/student001/knowledge-graph")
t_test_after = [n for n in after["nodes"] if n["id"] == "t_test"][0]
print(f"\n测试后 t检验 mastery: {t_test_after['mastery']:.2f}")
print(f"图谱同步: {'✅ 是' if abs(t_test_after['mastery'] - ku['mastery_after']) < 0.01 else '❌ 否'}")

print("\n" + "=" * 60)
print("闭环测试2：学生答对 → mastery上升")
print("=" * 60)

r2 = post(f"{BASE}/api/agent/chat", {
    "role": "student", "user_id": "student001",
    "message": "总体方差未知小样本应该用t分布，自由度是n-1",
    "current_knowledge_node": "t_test"
})
print(f"学生回答: '总体方差未知小样本应该用t分布'")
print(f"Evaluation: {r2['evaluation']['correctness']} (score: {r2['evaluation']['score']})")
ku2 = r2["knowledge_updates"][0]
print(f"mastery变化: {ku2['mastery_before']:.2f} → {ku2['mastery_after']:.2f} (Δ={ku2['mastery_delta']:+.3f})")
print(f"Help Level: L{r2['help_level']} (答对后降低帮助等级)")

print("\n" + "=" * 60)
print("闭环测试3：班级高频错因从DB聚合")
print("=" * 60)
misc = get(f"{BASE}/api/teacher/misconceptions")
print(f"数据来源: {misc['data_source']}")
print(f"错因数量: {len(misc['misconceptions'])}")
for m in misc["misconceptions"][:5]:
    print(f"  - {m['error_type']}: {m['total_count']}次, {m['student_count']}名学生")

print("\n" + "=" * 60)
print("闭环测试4：教师Dashboard真实数据")
print("=" * 60)
dash = get(f"{BASE}/api/teacher/dashboard")
print(f"平均掌握度: {dash['avg_mastery']:.0%}")
print(f"数据来源: {dash['data_source']}")
print(f"薄弱TOP3:")
for t in dash["weak_topics"][:3]:
    print(f"  - {t['name']}: {t['mastery']:.0%}")

print("\n✅ 闭环测试完成")
