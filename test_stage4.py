# -*- coding: utf-8 -*-
"""第四阶段API测试"""
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

def post(url, data, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=" * 60)
print("测试1：Demo Reset一键重置")
print("=" * 60)
r = post(f"{BASE}/api/demo/reset", {})
print(f"状态: {r['status']}")
print(f"消息: {r['message']}")
print(f"重置表: {r['tables_reset']}")

print("\n" + "=" * 60)
print("测试2：动态学习路径 - 验证重排序")
print("=" * 60)
path = get(f"{BASE}/api/student/student001/learning-path")
print(f"数据来源: {path['data_source']}")
print(f"路径节点数: {len(path['path'])}")
print("\n前5个节点（应该是最薄弱的）:")
for i, p in enumerate(path['path'][:5]):
    print(f"  {i+1}. {p['name']} - mastery={p['mastery']:.2f} ({p['status']})")

print("\n后3个节点（应该是已掌握的）:")
for i, p in enumerate(path['path'][-3:]):
    print(f"  {len(path['path'])-2+i}. {p['name']} - mastery={p['mastery']:.2f} ({p['status']})")

print("\n" + "=" * 60)
print("测试3：AI知识图谱生成（调智谱）")
print("=" * 60)
try:
    r = post(f"{BASE}/api/knowledge-graph/generate", {"topic": "正态总体均值的假设检验"}, timeout=60)
    print(f"来源: {r['source']}")
    print(f"节点数: {len(r['nodes'])}")
    print(f"边数: {len(r['edges'])}")
    if r['nodes']:
        print("前5个节点:")
        for n in r['nodes'][:5]:
            print(f"  - {n['name']}")
except Exception as e:
    print(f"请求超时或失败: {e}")
