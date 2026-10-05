# -*- coding: utf-8 -*-
"""Diagnosis Agent - 学习诊断"""
from __future__ import annotations
from typing import Any
from .base import BaseAgent, AgentResult


class DiagnosisAgent(BaseAgent):
    name = "Diagnosis Agent"
    description = "分析学生知识薄弱点和错误原因"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        node = context.get("knowledge_node", "未指定知识点")
        mastery = context.get("mastery", 0.5)

        if mastery < 0.3:
            analysis = f"知识点「{node}」掌握度较低（{mastery:.0%}），建议从基础概念重新梳理。"
        elif mastery < 0.6:
            analysis = f"知识点「{node}」处于学习阶段（{mastery:.0%}），建议通过例题巩固。"
        else:
            analysis = f"知识点「{node}」掌握较好（{mastery:.0%}），可以尝试综合应用。"

        return AgentResult(
            agent_name=self.name,
            task="知识诊断分析",
            summary=analysis,
            structured_data={"mastery": mastery, "node": node, "level": "weak" if mastery < 0.4 else "learning"},
            confidence=0.8,
        )
