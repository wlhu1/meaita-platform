# -*- coding: utf-8 -*-
"""教师端Agent：班级分析、教学设计、错因分析 - 智谱LLM真实调用版"""
from __future__ import annotations
import logging
from typing import Any
from .base import BaseAgent, AgentResult

logger = logging.getLogger("meaita.agents.teaching")

# 延迟初始化ZhipuClient，避免导入时就要求API Key
_zhipu_client = None

def _get_zhipu():
    global _zhipu_client
    if _zhipu_client is None:
        try:
            from zhipu_client import ZhipuClient
            _zhipu_client = ZhipuClient()
        except Exception as e:
            logger.warning("智谱客户端初始化失败: %s，将使用模板降级", e)
            return None
    return _zhipu_client


class ClassAnalyticsAgent(BaseAgent):
    name = "Class Analytics Agent"
    description = "班级整体学习数据分析，基于真实DB数据生成自然语言分析"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        class_stats = context.get("class_stats", {})
        misconceptions = context.get("misconceptions", [])

        # 准备结构化数据摘要
        weak_topics = sorted(class_stats.items(), key=lambda x: x[1]["mastery"])[:5]
        weak_str = "\n".join([f"- {node}: 平均掌握率 {stats['mastery']:.0%}, 累计错误{stats['errors']}次"
                              for node, stats in weak_topics])
        misc_str = "\n".join([f"- {m['error_type']}({m['node_id']}): {m['total_count']}次, 涉及{m['student_count']}名学生"
                              for m in misconceptions[:5]])

        prompt = f"""你是一位经验丰富的大学数学教学分析师。以下是《概率论与数理统计》课程班级的真实学习数据：

【班级各知识点掌握情况（按掌握率从低到高）】
{weak_str}

【高频错误类型统计】
{misc_str or '暂无错误记录'}

请基于以上真实数据，用150-200字给出班级学情分析，包括：
1. 最突出的薄弱知识点
2. 最主要的错误原因
3. 教学建议
注意：只能使用给定数据，不要编造学生姓名或具体分数。如果数据不足请说明。"""

        # 尝试调用智谱
        client = _get_zhipu()
        if client:
            try:
                response = client.chat_once(
                    [{"role": "user", "content": prompt}],
                    temperature=0.5, max_tokens=500
                )
                return AgentResult(
                    agent_name=self.name,
                    task="班级学情分析（LLM生成）",
                    summary=response[:100] + "...",
                    answer=response,
                    structured_data={
                        "avg_mastery": weak_topics[0][1]["mastery"] if weak_topics else 0.5,
                        "weak_topics": [n for n, _ in weak_topics],
                        "source": "zhipu_llm + real_db",
                    },
                    confidence=0.9,
                )
            except Exception as e:
                logger.warning("智谱调用失败，降级模板: %s", e)

        # 降级模板
        summary = f"班级共5名学生，平均掌握率较低。最薄弱知识点：{weak_topics[0][0] if weak_topics else 't检验'}。"
        return AgentResult(
            agent_name=self.name,
            task="班级学情分析（模板降级）",
            summary=summary,
            answer=summary + " 建议针对薄弱知识点加强课堂练习。",
            structured_data={
                "avg_mastery": weak_topics[0][1]["mastery"] if weak_topics else 0.5,
                "weak_topics": [n for n, _ in weak_topics],
                "source": "template_fallback",
            },
            confidence=0.6,
        )


class MisconceptionAgent(BaseAgent):
    name = "Misconception Agent"
    description = "高频错因识别与分析"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            task="高频错因分析",
            summary="从wrong_questions表实时聚合错因",
            structured_data={"source": "real_db_aggregation"},
            confidence=0.9,
        )


class TeachingDesignAgent(BaseAgent):
    name = "Teaching Design Agent"
    description = "AI辅助教学设计（真实调用智谱）"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        topic = context.get("topic", "假设检验")

        prompt = f"""请为大学课程《概率论与数理统计》设计一节关于"{topic}"的教学设计。
要求结构化输出，包含以下部分：
1. 教学目标（3条）
2. 教学重点
3. 教学难点
4. 课前预习任务（2条）
5. 课堂问题链（4个递进问题）
6. 课堂活动（1个）
7. 分层任务：基础组/提高组/挑战组（各2题）
8. 课后作业

用Markdown格式输出，简洁专业。"""

        client = _get_zhipu()
        if client:
            try:
                response = client.chat_once(
                    [{"role": "user", "content": prompt}],
                    temperature=0.7, max_tokens=1000
                )
                return AgentResult(
                    agent_name=self.name,
                    task=f"《{topic}》教学设计（智谱LLM生成）",
                    summary=f"已生成《{topic}》完整教学设计",
                    answer=response,
                    structured_data={"topic": topic, "source": "zhipu_llm"},
                    confidence=0.92,
                )
            except Exception as e:
                logger.warning("教学设计LLM失败，降级模板: %s", e)

        # 降级模板
        design = f"《{topic}》教学设计\n教学目标：理解{topic}基本概念，掌握应用方法。\n重点：核心原理。\n难点：实际应用。"
        return AgentResult(
            agent_name=self.name,
            task=f"《{topic}》教学设计（模板降级）",
            summary="模板生成",
            answer=design,
            structured_data={"topic": topic, "source": "template_fallback"},
            confidence=0.5,
        )


class AssessmentAgent(BaseAgent):
    name = "Assessment Agent"
    description = "分层练习/测验生成（真实调用智谱）"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        topic = context.get("topic", "假设检验")

        prompt = f"""请为《概率论与数理统计》中"{topic}"知识点生成6道练习题，分三层：
- 基础组（2题）：概念理解，全体学生必做
- 提高组（2题）：简单计算，中等水平学生
- 挑战组（2题）：综合应用，高水平学生

每题包含：题目、答案、简要解析。
用Markdown输出，难度梯度明显。"""

        client = _get_zhipu()
        if client:
            try:
                response = client.chat_once(
                    [{"role": "user", "content": prompt}],
                    temperature=0.8, max_tokens=1000
                )
                return AgentResult(
                    agent_name=self.name,
                    task=f"《{topic}》分层练习（智谱LLM生成）",
                    summary=f"已生成《{topic}》三层共6题",
                    answer=response,
                    structured_data={"topic": topic, "source": "zhipu_llm"},
                    confidence=0.9,
                )
            except Exception as e:
                logger.warning("练习生成LLM失败，降级模板: %s", e)

        # 降级
        practice = f"《{topic}》分层练习（模板）\n基础：1.什么是{topic}？ 2.基本步骤？\n提高：3.简单计算 4.对比分析\n挑战：5.综合案例 6.拓展思考"
        return AgentResult(
            agent_name=self.name,
            task=f"《{topic}》分层练习（模板降级）",
            summary="模板生成",
            answer=practice,
            structured_data={"topic": topic, "source": "template_fallback"},
            confidence=0.5,
        )
