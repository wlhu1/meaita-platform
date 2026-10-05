# -*- coding: utf-8 -*-
"""ME-AITA 数字素养诊断 API（试用版）"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from database import get_db
from diagnosis_engine import (
    IDENTITIES,
    QUESTION_BANK,
    STAGES,
    SUBJECTS,
    build_report,
)

router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])


class DiagnosisSubmit(BaseModel):
    identity: str = Field(min_length=1, max_length=20)
    stage: str = Field(min_length=1, max_length=20)
    subject: str = Field(min_length=1, max_length=20)
    answers: dict = Field(min_length=1)


@router.get("/meta")
def get_meta():
    return {
        "trial": True,
        "trial_note": "本测评为试用版基础测评，依据《教师数字素养》（JY/T 0646—2022）五维度设计，非正式能力评价。",
        "identities": IDENTITIES,
        "stages": STAGES,
        "subjects": SUBJECTS,
    }


@router.get("/questions")
def get_questions():
    return {"trial": True, "dimensions_note": "维度：数字意识 / 数字技术知识与技能 / 数字化教学应用 / 数字化专业发展 / 数字社会责任", "questions": QUESTION_BANK}


@router.post("/submit")
def submit_diagnosis(body: DiagnosisSubmit):
    # 合法性检查：答案必须覆盖全部题目，值在 1-5 之间
    expected = {q["id"] for q in QUESTION_BANK}
    provided = set(body.answers.keys())
    if not expected.issubset(provided):
        missing = sorted(expected - provided)
        return {"ok": False, "message": f"尚有题目未作答：{len(missing)} 题，请完成后提交。", "missing": missing}

    report = build_report(body.answers)
    db = get_db()
    record_id = db.add_diagnosis(
        identity=body.identity,
        stage=body.stage,
        subject=body.subject,
        answers=body.answers,
        scores=report["scores"],
        total_score=report["total"],
        level=report["level"],
    )
    return {"ok": True, "record_id": record_id, "report": report}


@router.get("/records")
def list_records(limit: int = 20):
    records = get_db().list_diagnosis(limit=limit)
    return {"records": records}
