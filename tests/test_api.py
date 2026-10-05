# -*- coding: utf-8 -*-
"""ME-AITA 后端接口自动化测试（不依赖外部大模型，离线可运行）。

运行：venv\\Scripts\\python.exe -m pytest tests/test_api.py -v
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "model" in data


def test_info_no_key_leak():
    r = client.get("/api/info")
    assert r.status_code == 200
    text = r.text
    # 不应泄露完整密钥
    assert "l1XMVjvIy4Cki4hI" not in text
    assert "ZHIPU_API_KEY" not in text


def test_index_page():
    r = client.get("/")
    assert r.status_code == 200
    assert "ME-AITA" in r.text


def test_diagnosis_page():
    r = client.get("/diagnosis.html")
    assert r.status_code == 200
    assert "数字素养诊断" in r.text


def test_resources_page():
    r = client.get("/resources.html")
    assert r.status_code == 200
    assert "优质资源推荐" in r.text


def test_session_crud():
    # 新建
    r = client.post("/api/sessions", json={"title": "测试会话"})
    assert r.status_code == 200
    sid = r.json()["session"]["id"]
    # 列表
    r = client.get("/api/sessions")
    ids = [s["id"] for s in r.json()["sessions"]]
    assert sid in ids
    # 改名
    r = client.post(f"/api/sessions/{sid}/rename", json={"title": "改名会话"})
    assert r.json()["session"]["title"] == "改名会话"
    # 删除
    r = client.delete(f"/api/sessions/{sid}")
    assert r.json()["ok"] is True
    # 删除后不存在
    r = client.get(f"/api/sessions/{sid}/messages")
    assert r.status_code == 404


def test_chat_stream_validation():
    # 空消息应 400
    r = client.post("/api/chat/stream", json={"message": ""})
    assert r.status_code == 400
    # 不存在的会话应 404
    r = client.post("/api/chat/stream", json={"session_id": 999999, "message": "你好"})
    assert r.status_code == 404


def test_diagnosis_meta_and_questions():
    r = client.get("/api/diagnosis/meta")
    assert r.status_code == 200
    assert r.json()["trial"] is True
    r = client.get("/api/diagnosis/questions")
    qs = r.json()["questions"]
    assert len(qs) == 15
    dims = {q["dimension"] for q in qs}
    assert len(dims) == 5  # 五个维度


def test_diagnosis_submit_full():
    answers = {f"d{i//3+1}q{i%3+1}": 5 for i in range(15)}
    r = client.post("/api/diagnosis/submit", json={
        "identity": "在职教师", "stage": "初中", "subject": "数学", "answers": answers
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    report = data["report"]
    assert report["total"] == 75  # 全 5 分
    assert report["level"] == "优秀"
    assert len(report["dimensions"]) == 5
    assert "试用版" in report["trial_note"]


def test_diagnosis_submit_missing():
    answers = {"d1q1": 3}
    r = client.post("/api/diagnosis/submit", json={
        "identity": "师范生", "stage": "小学", "subject": "语文", "answers": answers
    })
    data = r.json()
    assert data["ok"] is False
    assert len(data["missing"]) == 14


def test_resources_seed_and_filter():
    r = client.get("/api/resources")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 10  # 种子资源已导入
    # 类别过滤
    r = client.get("/api/resources", params={"category": "课程标准"})
    items = r.json()["resources"]
    assert all(i["category"] == "课程标准" for i in items)
    # 关键词
    r = client.get("/api/resources", params={"q": "智慧教育平台"})
    assert len(r.json()["resources"]) >= 1


def test_resources_import_validation():
    r = client.post("/api/resources/import", json={"resources": [
        {"name": "测试资源", "category": "不存在的类别"}
    ]})
    assert r.status_code == 400
