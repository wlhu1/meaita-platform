# -*- coding: utf-8 -*-
"""Knowledge Agent - 知识点讲解"""
from __future__ import annotations
from typing import Any
from .base import BaseAgent, AgentResult


class KnowledgeAgent(BaseAgent):
    name = "Knowledge Agent"
    description = "提供知识点的系统讲解"

    def run(self, message: str, context: dict[str, Any] | None = None) -> AgentResult:
        context = context or {}
        node = context.get("knowledge_node", "")

        explanations = {
            "t_test": """**t检验（t Test）**

t检验是用于**总体标准差未知**、**样本量较小（n<30）**时，对总体均值进行检验的方法。

**核心公式：**
$$t = \\frac{\\bar{x} - \\mu_0}{s / \\sqrt{n}}$$

其中：
- $\\bar{x}$ 是样本均值
- $\\mu_0$ 是原假设的总体均值
- $s$ 是样本标准差
- $n$ 是样本量

**与Z检验的区别：**
- Z检验：总体标准差σ已知 → 用标准正态分布
- t检验：总体标准差σ未知 → 用t分布（自由度df=n-1）

**适用场景：**
1. 单样本t检验：比较样本均值与已知总体均值
2. 独立样本t检验：比较两组均值
3. 配对t检验：比较配对数据的差异""",

            "hypothesis_test": """**假设检验（Hypothesis Testing）**

假设检验是统计推断的一种方法，通过样本数据来判断对总体参数的假设是否成立。

**基本步骤：**
1. 提出原假设 $H_0$ 和备择假设 $H_1$
2. 选择显著性水平 $\\alpha$（通常取0.05）
3. 构造检验统计量
4. 计算p值或确定拒绝域
5. 做出决策：p < α → 拒绝$H_0$

**两类错误：**
- 第一类错误（弃真）：$H_0$为真却拒绝了，概率为α
- 第二类错误（取伪）：$H_0$为假却没拒绝，概率为β""",
        }

        answer = explanations.get(node, f"关于「{node}」的详细讲解正在生成中。这是一个重要知识点，建议结合教材和例题理解。")

        return AgentResult(
            agent_name=self.name,
            task="知识点系统讲解",
            summary=f"讲解知识点：{node}",
            answer=answer,
            structured_data={"node": node},
            confidence=0.85,
        )
