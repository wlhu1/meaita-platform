# -*- coding: utf-8 -*-
"""Learning Path Agent - 个性化学习路径规划"""
from __future__ import annotations
from typing import Any
from .base import BaseAgent, AgentResult


class LearningPathAgent(BaseAgent):
    name = "Learning Path Agent"
    description = "根据学生掌握情况规划个性化学习路径"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        weak_nodes = context.get("weak_nodes", [])

        if weak_nodes:
            summary = f"发现{len(weak_nodes)}个薄弱知识点，建议优先攻克：" + "、".join(weak_nodes[:3])
        else:
            summary = "当前各知识点掌握均衡，建议进入综合练习阶段。"

        return AgentResult(
            agent_name=self.name,
            task="学习路径规划",
            summary=summary,
            structured_data={"weak_nodes": weak_nodes, "priority": weak_nodes[:3]},
            confidence=0.8,
        )
