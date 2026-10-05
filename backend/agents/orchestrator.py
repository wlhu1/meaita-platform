# -*- coding: utf-8 -*-
"""Orchestrator Agent - 教学场景识别与多Agent路由"""
from __future__ import annotations
import re
from typing import Any
from .base import BaseAgent, AgentResult


class Orchestrator(BaseAgent):
    name = "Orchestrator"
    description = "识别教学场景（课前/课中/课后）和用户意图，路由到对应Agent"
    system_prompt = "你是教学场景路由器，负责判断用户提问属于哪个教学阶段和意图。"

    # 场景关键词
    PRE_CLASS_KEYWORDS = [
        "明天", "下次课", "预习", "课前", "应该先复习", "应该先学", "应该复习",
        "接下来学什么", "下一章", "准备", "导入", "前导知识", "开始学习",
        "要学", "之前没学", "还没学",
    ]
    IN_CLASS_KEYWORDS = [
        "为什么", "怎么理解", "不对", "不懂", "不会做", "这道题", "什么意思",
        "怎么算", "为什么不能", "区别", "哪里错", "解释", "方差未知",
        "Z检验", "t检验", "怎么用", "怎么回事",
        "怎么做", "题目", "不会", "求解", "步骤",
        "假设检验", "检验", "求", "计算",
    ]
    POST_CLASS_KEYWORDS = [
        "总结", "今天学了", "哪里不会", "回顾", "今天内容", "错题", "薄弱",
        "掌握情况", "进步", "反思", "学完了", "今天还有", "总结一下",
    ]

    # 意图关键词
    INTENT_PATTERNS = {
        "explanation": ["解释", "什么是", "为什么", "怎么理解", "含义"],
        "diagnosis": ["哪里错", "为什么不对", "错误", "不会", "薄弱"],
        "practice": ["练习", "做题", "再来一道", "测验", "测试"],
        "planning": ["学习计划", "路径", "应该先学", "规划"],
        "reflection": ["总结", "回顾", "反思", "今天哪里"],
        "wrong_question": ["错题", "订正", "这道题错了"],
        "knowledge_graph": ["知识图谱", "知识结构", "关联"],
        "teaching_design": ["教学设计", "备课", "教案", "课时", "教学设计"],
        "class_analysis": ["班级", "学生情况", "平均", "整体", "分析一下", "掌握情况", "这个班", "学情"],
        "assessment": ["出卷", "生成题目", "测验", "考试", "练习", "出题"],
    }

    def detect_phase(self, message: str) -> str:
        """判断教学阶段：PRE_CLASS / IN_CLASS / POST_CLASS / GENERAL"""
        msg = message.lower()
        pre_score = sum(1 for kw in self.PRE_CLASS_KEYWORDS if kw in msg)
        in_score = sum(1 for kw in self.IN_CLASS_KEYWORDS if kw in msg)
        post_score = sum(1 for kw in self.POST_CLASS_KEYWORDS if kw in msg)

        if pre_score >= in_score and pre_score >= post_score and pre_score > 0:
            return "PRE_CLASS"
        if post_score >= in_score and post_score > 0:
            return "POST_CLASS"
        if in_score > 0:
            return "IN_CLASS"
        return "GENERAL"

    def detect_intent(self, message: str) -> str:
        """判断用户意图"""
        msg = message.lower()
        best_intent = "general"
        best_score = 0
        for intent, keywords in self.INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in msg)
            if score > best_score:
                best_score = score
                best_intent = intent
        return best_intent

    def select_agents(self, phase: str, intent: str, role: str = "student") -> list[dict]:
        """根据场景和意图选择活跃Agent"""
        agents = []

        if role == "student":
            # 学生端Agent组合
            if phase == "PRE_CLASS":
                agents = [
                    {"name": "Diagnosis Agent", "task": "前置知识诊断", "status": "done"},
                    {"name": "Knowledge Agent", "task": "知识点预习讲解", "status": "done"},
                    {"name": "Learning Path Agent", "task": "规划预习路径", "status": "done"},
                ]
            elif phase == "IN_CLASS":
                if intent in ("diagnosis", "explanation"):
                    agents = [
                        {"name": "Diagnosis Agent", "task": "分析知识错误点", "status": "done"},
                        {"name": "Pedagogy Agent", "task": "确定帮助级别", "status": "done"},
                        {"name": "Socratic Tutor", "task": "生成分级引导提示", "status": "done"},
                    ]
                elif intent == "practice":
                    agents = [
                        {"name": "Diagnosis Agent", "task": "定位薄弱知识点", "status": "done"},
                        {"name": "Practice Generator", "task": "生成针对性练习", "status": "done"},
                    ]
                else:
                    agents = [
                        {"name": "Knowledge Agent", "task": "知识点讲解", "status": "done"},
                        {"name": "Socratic Tutor", "task": "引导思考", "status": "done"},
                    ]
            elif phase == "POST_CLASS":
                agents = [
                    {"name": "Reflection Agent", "task": "课堂内容回顾", "status": "done"},
                    {"name": "Diagnosis Agent", "task": "学习效果诊断", "status": "done"},
                    {"name": "Learning Path Agent", "task": "调整后续学习计划", "status": "done"},
                ]
            else:
                agents = [
                    {"name": "Knowledge Agent", "task": "通用知识解答", "status": "done"},
                ]
        else:
            # 教师端Agent组合
            if intent == "teaching_design":
                agents = [
                    {"name": "Teaching Design Agent", "task": "生成教学设计方案", "status": "done"},
                    {"name": "Class Analytics Agent", "task": "分析班级学情", "status": "done"},
                ]
            elif intent == "class_analysis":
                agents = [
                    {"name": "Class Analytics Agent", "task": "班级整体分析", "status": "done"},
                    {"name": "Misconception Agent", "task": "高频错因识别", "status": "done"},
                ]
            elif intent == "assessment":
                agents = [
                    {"name": "Assessment Agent", "task": "生成分层练习", "status": "done"},
                    {"name": "Class Analytics Agent", "task": "依据学情分层", "status": "done"},
                ]
            else:
                agents = [
                    {"name": "Teaching Design Agent", "task": "教学支持", "status": "done"},
                ]

        # 始终把Orchestrator放第一位
        return [{"name": "Orchestrator", "task": "场景识别与路由", "status": "done"}] + agents

    def determine_help_level(self, intent: str, wrong_count: int = 0) -> int:
        """确定Help Ladder级别（1-5）"""
        if intent == "explanation":
            return 3  # 知识点提示
        if intent == "diagnosis":
            return 2 if wrong_count < 3 else 3
        if intent == "practice":
            return 1
        return 2

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        role = context.get("role", "student")

        phase = self.detect_phase(message)
        intent = self.detect_intent(message)
        active_agents = self.select_agents(phase, intent, role)
        help_level = self.determine_help_level(intent, context.get("wrong_count", 0))

        return AgentResult(
            agent_name=self.name,
            task="场景识别与路由",
            summary=f"识别为{phase}场景，意图：{intent}",
            structured_data={
                "phase": phase,
                "intent": intent,
                "active_agents": active_agents,
                "help_level": help_level,
            },
            confidence=0.9,
        )
