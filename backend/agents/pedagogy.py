# -*- coding: utf-8 -*-
"""Pedagogy Agent - 教学策略与Help Ladder"""
from __future__ import annotations
from typing import Any
from .base import BaseAgent, AgentResult


class PedagogyAgent(BaseAgent):
    name = "Pedagogy Agent"
    description = "根据Help Ladder决定提示级别，避免直接给答案"

    HELP_LEVELS = {
        1: "反思引导：让学生自己回顾思路，找出问题所在",
        2: "方向提示：给出思考方向，不透露具体步骤",
        3: "知识点提示：提示需要用到的核心概念",
        4: "部分步骤：给出前几步，让学生完成剩余",
        5: "完整讲解：完整的解题过程和原理",
    }

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        help_level = context.get("help_level", 2)
        node = context.get("knowledge_node", "")

        hints = {
            "t_test": {
                1: "你先回忆一下，t检验和Z检验最关键的区别是什么？",
                2: "思考一下：题目中总体标准差是已知还是未知？这会影响我们用什么分布。",
                3: "当总体方差未知时，我们用t分布代替正态分布。回忆t统计量的公式。",
                4: "第一步：计算样本均值和样本标准差；第二步：计算t统计量 = (x̄ - μ₀) / (s/√n)；第三步：查t分布表。",
                5: f"完整讲解：这道题应该用t检验。因为总体标准差σ未知，且样本量n=16<30。\n"
                   f"步骤：1) H0: μ=20, H1: μ≠20  2) 计算t值 = (20.5-20)/(2/√16) = 1.0\n"
                   f"3) 自由度df=15，α=0.05双侧临界值为±2.131  4) |t|=1.0 < 2.131，不拒绝H0",
            },
            "hypothesis_test": {
                1: "你觉得p值的大小和拒绝H0之间是什么关系？",
                2: "回忆一下显著性水平α的含义，它和p值怎么比较？",
                3: "p值是当H0为真时，观察到当前或更极端结果的概率。p<α意味着什么？",
                4: "决策规则：p < α → 拒绝H0；p ≥ α → 不拒绝H0。",
                5: f"完整讲解：假设检验的决策逻辑是——p值是在H0成立的前提下，出现当前样本结果的概率。"
                   f"如果这个概率很小（小于显著性水平α），说明H0成立时出现当前样本很罕见，因此我们拒绝H0。"
                   f"所以p<α时应该拒绝原假设。",
            },
        }

        node_hints = hints.get(node, {})
        hint_text = node_hints.get(help_level, f"建议从基础概念入手，逐步思考。当前帮助级别：L{help_level}")

        return AgentResult(
            agent_name=self.name,
            task=f"Help Ladder L{help_level}提示生成",
            summary=f"当前帮助级别：L{help_level} - {self.HELP_LEVELS.get(help_level, '')}",
            answer=hint_text,
            structured_data={"help_level": help_level, "level_desc": self.HELP_LEVELS.get(help_level, "")},
            confidence=0.85,
        )
