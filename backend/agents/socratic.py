# -*- coding: utf-8 -*-
"""Socratic Tutor - 苏格拉底式引导提问（真实调用智谱LLM）"""
from __future__ import annotations
import logging
from typing import Any
from .base import BaseAgent, AgentResult

logger = logging.getLogger("meaita.agents.socratic")

_zhipu_client = None

def _get_zhipu():
    global _zhipu_client
    if _zhipu_client is None:
        try:
            from zhipu_client import ZhipuClient
            _zhipu_client = ZhipuClient()
        except Exception as e:
            logger.warning("智谱客户端初始化失败: %s", e)
            return None
    return _zhipu_client


# Help Level对应的教学策略
HELP_LEVEL_GUIDE = {
    1: "L1反思级：只提开放性反思问题，不给任何提示，让学生自己回顾思路。",
    2: "L2方向级：提供方向性提示，但不给关键步骤和答案，引导学生自己找到方法。",
    3: "L3知识点级：指出相关知识点和核心方法，但不展开完整解题过程。",
    4: "L4部分步骤级：给出解题的前1-2步，让学生继续完成剩余部分。",
    5: "L5完整讲解级：可以完整解释概念和解题过程，因为学生已经多次尝试仍有困难。",
}


class SocraticTutor(BaseAgent):
    name = "Socratic Tutor"
    description = "苏格拉底式学习辅导，根据Help Level控制帮助程度，调用智谱生成回复"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        ctx = context or {}
        node = ctx.get("knowledge_node", "")
        help_level = ctx.get("help_level", 2)
        mastery = ctx.get("mastery", 0.3)
        correctness = ctx.get("correctness", "unknown")
        error_type = ctx.get("error_type", "")
        pedagogy_hint = ctx.get("pedagogy_hint", "")

        help_guide = HELP_LEVEL_GUIDE.get(help_level, HELP_LEVEL_GUIDE[2])

        prompt = f"""你是一位苏格拉底式的大学数学学习辅导老师。请根据学生情况给出回复。

【学生当前情况】
- 知识点：{node}
- 学生掌握度：{mastery:.0%}
- 上一轮回答评价：{correctness}
- 错误类型：{error_type if error_type else '无'}
- 当前帮助等级：L{help_level}

【教学要求】
{help_guide}
- 不要直接给出最终答案，除非Help Level=5
- 用引导式提问或提示，语气友好鼓励
- 回答控制在100字以内，简洁
- 用中文回答

【学生说的话】
{message}
"""

        client = _get_zhipu()
        if client:
            try:
                response = client.chat_once(
                    [{"role": "user", "content": prompt}],
                    temperature=0.7, max_tokens=300
                )
                return AgentResult(
                    agent_name=self.name,
                    task=f"Socratic辅导（L{help_level}，智谱生成）",
                    summary=f"根据Help L{help_level}生成引导回复",
                    answer=response,
                    structured_data={
                        "help_level": help_level,
                        "generation_source": "zhipu",
                    },
                    confidence=0.9,
                )
            except Exception as e:
                logger.warning("智谱调用失败，降级模板: %s", e)

        # 降级模板
        fallback_questions = {
            "t_test": "你能先告诉我，你觉得这道题为什么不能用Z检验吗？",
            "hypothesis_test": "你先说说，假设检验的基本思想是什么？",
        }
        fallback = fallback_questions.get(node, "你先说说你对这个问题的理解，卡在哪里了？")

        return AgentResult(
            agent_name=self.name,
            task=f"Socratic辅导（L{help_level}，本地降级）",
            summary="模板引导回复",
            answer=fallback,
            structured_data={
                "help_level": help_level,
                "generation_source": "local_fallback",
            },
            confidence=0.5,
        )
