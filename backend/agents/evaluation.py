# -*- coding: utf-8 -*-
"""Evaluation Agent - 学生回答评价与掌握度更新"""
from __future__ import annotations
from typing import Any
from .base import BaseAgent, AgentResult


class EvaluationAgent(BaseAgent):
    name = "Evaluation Agent"
    description = "评价学生回答正确性，输出结构化评价结果并触发掌握度更新"
    system_prompt = """你是一个教学评价专家。根据学生回答和知识点，判断学生回答的正确性、错误类型，并给出具体反馈。"""

    # 错误类型词典（演示用，后续可扩展）
    ERROR_TYPES = {
        "z_t_confusion": "Z检验与t检验适用条件混淆",
        "one_two_sided": "单侧/双侧检验判断错误",
        "hypothesis_direction": "原假设/备择假设方向错误",
        "alpha_misunderstand": "显著性水平理解错误",
        "rejection_region": "拒绝域判断错误",
        "concept_misunderstanding": "基本概念理解偏差",
        "calculation_error": "计算错误",
        "no_answer": "未作答或完全无法回答",
    }

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        ctx = context or {}
        student_answer = message
        knowledge_node = ctx.get("knowledge_node", "unknown")
        question = ctx.get("question", "")
        help_level = ctx.get("help_level", 2)
        current_mastery = ctx.get("current_mastery", 0.3)

        # ===== 规则式评价（后续可替换为LLM） =====
        correctness, score, error_type, feedback = self._evaluate_by_rules(
            student_answer, knowledge_node, question, help_level
        )

        # ===== 计算掌握度变化 =====
        mastery_delta = self._calc_mastery_delta(correctness, help_level, current_mastery)
        error_inc = 1 if correctness in ("incorrect", "partially_correct") else 0

        structured = {
            "correctness": correctness,
            "score": score,
            "knowledge_node": knowledge_node,
            "error_type": error_type,
            "error_type_desc": self.ERROR_TYPES.get(error_type, "未知错误"),
            "feedback": feedback,
            "mastery_delta": mastery_delta,
            "error_inc": error_inc,
            "evidence_summary": f"学生回答: {student_answer[:50]}...",
            "help_level_at_answer": help_level,
        }

        return AgentResult(
            agent_name=self.name,
            task="评价学生回答并计算掌握度变化",
            summary=f"评价结果: {correctness} (得分: {score:.1f}), mastery变化: {mastery_delta:+.2f}",
            answer=feedback,
            structured_data=structured,
            confidence=0.8,
        )

    def _evaluate_by_rules(self, answer: str, node: str, question: str, help_level: int):
        """规则式评价：根据回答关键词判断正确性"""
        ans = answer.strip()

        # 空回答或明确不会
        if not ans or any(kw in ans for kw in ["不会", "不知道", "不清楚", "没思路"]):
            return "incorrect", 0.1, "no_answer", "没关系，我们一步步来。先想想：这个问题涉及的基本概念是什么？"

        # 包含正确关键词的情况
        correct_keywords = {
            "z_test": ["总体方差已知", "大样本", "标准正态", "Z分布"],
            "t_test": ["总体方差未知", "小样本", "t分布", "自由度"],
            "hypothesis_test": ["原假设", "备择假设", "显著性水平", "拒绝域"],
            "p_value": ["p值", "显著性水平", "拒绝原假设"],
        }

        # 包含错误关键词的情况
        wrong_keywords = {
            "z_t_confusion": ["方差未知用Z", "小样本用Z"],
            "one_two_sided": ["单侧双侧一样", "随便选单侧"],
        }

        # 检查错误关键词
        for error_type, keywords in wrong_keywords.items():
            if any(kw in ans for kw in keywords):
                desc = self.ERROR_TYPES.get(error_type, "概念错误")
                feedback = f"这里需要注意：{desc}。你可以再回忆一下Z检验和t检验的区别是什么？"
                return "partially_correct", 0.4, error_type, feedback

        # 检查正确关键词
        node_keywords = correct_keywords.get(node, [])
        if node_keywords and any(kw in ans for kw in node_keywords):
            feedback = "很好！你抓住了关键要点。能不能再具体展开说明一下？"
            return "correct", 0.85, None, feedback

        # 默认：部分正确
        return "partially_correct", 0.5, "concept_misunderstanding", "思路有一定道理，但还不够完整。你再想想核心条件是什么？"

    def _calc_mastery_delta(self, correctness: str, help_level: int, current_mastery: float) -> float:
        """根据评价结果计算掌握度变化（保守规则）"""
        if correctness == "correct":
            if help_level <= 2:
                delta = 0.08  # 独立答对，进步大
            elif help_level <= 3:
                delta = 0.04  # 中等提示后答对
            else:
                delta = 0.01  # 强提示后答对，进步小
        elif correctness == "partially_correct":
            delta = 0.01
        else:  # incorrect
            delta = -0.03

        # 限制范围
        new_mastery = max(0.05, min(0.95, current_mastery + delta))
        return round(new_mastery - current_mastery, 3)
