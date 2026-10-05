# -*- coding: utf-8 -*-
"""Agent 基础接口"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Agent 执行结果"""
    agent_name: str
    task: str
    summary: str = ""
    answer: str = ""
    structured_data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    status: str = "done"


class BaseAgent:
    """所有Agent的基类"""
    name: str = "BaseAgent"
    description: str = ""
    system_prompt: str = ""

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        """执行Agent任务，子类必须实现"""
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.name}>"
