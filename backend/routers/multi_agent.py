# -*- coding: utf-8 -*-
"""多智能体教学平台 API 路由 - 完整闭环版"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from database import get_db
from agents.orchestrator import Orchestrator
from agents.diagnosis import DiagnosisAgent
from agents.pedagogy import PedagogyAgent
from agents.socratic import SocraticTutor
from agents.knowledge import KnowledgeAgent
from agents.learning_path import LearningPathAgent
from agents.evaluation import EvaluationAgent
from agents.teaching import (
    ClassAnalyticsAgent, MisconceptionAgent, TeachingDesignAgent, AssessmentAgent
)

router = APIRouter(prefix="/api", tags=["multi-agent"])

orchestrator = Orchestrator()
evaluator = EvaluationAgent()

# 内存中记录每个学生当前的对话上下文（生产环境应放DB/Redis）
_chat_context: dict[str, dict] = {}


class AgentChatRequest(BaseModel):
    role: str = "student"
    user_id: str = "student001"
    course_id: int | None = None
    session_id: int | None = None
    message: str
    current_knowledge_node: str | None = None
    help_level: int | None = None
    wrong_question_id: int | None = None  # 从错题页带过来


@router.post("/agent/chat")
async def agent_chat(req: AgentChatRequest) -> dict[str, Any]:
    """多智能体统一聊天接口 - Evaluation驱动完整闭环"""
    db = get_db()

    # ===== 1. Orchestrator 场景识别 =====
    orch_result = orchestrator.run(req.message, context={"role": req.role})
    phase = orch_result.structured_data["phase"]
    intent = orch_result.structured_data["intent"]

    # ===== 2. 获取学生上下文 =====
    user = db.get_user_by_username(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    course_id = req.course_id or db.get_course_id_by_name("概率论与数理统计")
    states = db.get_learner_state(user["id"], course_id)
    state_map = {s["node_id"]: s for s in states}

    weak_nodes = [n for n, s in state_map.items() if s["status"] in ("weak", "unlearned")]
    current_node = req.current_knowledge_node or (weak_nodes[0] if weak_nodes else "hypothesis_test")
    current_state = state_map.get(current_node, {"mastery": 0.3, "error_count": 1, "status": "weak"})

    user_key = f"{user['id']}_{course_id}"
    ctx = _chat_context.get(user_key, {"consecutive_wrong": 0, "help_level": 2, "current_question": ""})

    # ===== 3. 学生端：Evaluation → Diagnosis → Pedagogy → Socratic 闭环 =====
    answer_parts = []
    actual_agents_run = []
    eval_result = None
    mastery_delta = 0
    error_inc = 0

    if req.role == "student":
        # --- Evaluation Agent 评价学生回答 ---
        eval_result = evaluator.run(req.message, context={
            "knowledge_node": current_node,
            "current_mastery": current_state["mastery"],
            "help_level": ctx["help_level"],
            "question": ctx.get("current_question", ""),
        })
        eval_data = eval_result.structured_data
        actual_agents_run.append({"name": "Evaluation Agent", "task": "评价学生回答", "status": "done"})

        correctness = eval_data["correctness"]
        mastery_delta = eval_data["mastery_delta"]
        error_inc = eval_data["error_inc"]

        # --- 错题自动入库 ---
        wrong_id = None
        if correctness in ("incorrect", "partially_correct"):
            # 用当前知识点问题作为错题题干
            question_text = ctx.get("current_question") or f"【{current_node}】相关概念辨析题"
            wrong_id = db.add_wrong_question(
                user_id=user["id"],
                course_id=course_id,
                node_id=current_node,
                question=question_text,
                user_answer=req.message,
                correct_answer="（待AI解析后补充）",
                misconception=eval_data.get("error_type_desc", ""),
                error_type=eval_data.get("error_type", ""),
                help_level=ctx["help_level"],
            )
            actual_agents_run.append({"name": "System", "task": "错题自动入库", "status": "done"})

        # --- 更新连续错误计数和Help Level ---
        if correctness == "correct":
            ctx["consecutive_wrong"] = 0
            # 答对了，降低帮助等级（下次更独立）
            ctx["help_level"] = max(1, ctx["help_level"] - 1)
        else:
            ctx["consecutive_wrong"] += 1
            # 综合mastery和连续错误次数计算Help Level
            if current_state["mastery"] < 0.3 or ctx["consecutive_wrong"] >= 3:
                ctx["help_level"] = min(5, ctx["help_level"] + 1)
            elif ctx["consecutive_wrong"] >= 1:
                ctx["help_level"] = min(4, ctx["help_level"] + 1)

        final_help_level = ctx["help_level"]

        # --- Diagnosis Agent 分析错因 ---
        diag = DiagnosisAgent().run(req.message, context={
            "knowledge_node": current_node,
            "mastery": current_state["mastery"],
            "error_type": eval_data.get("error_type", ""),
        })
        actual_agents_run.append({"name": "Diagnosis Agent", "task": "分析知识错误与错因", "status": "done"})

        # --- 更新learner_states ---
        updated = db.update_learner_state(
            user["id"], course_id, current_node,
            mastery_delta=mastery_delta, error_inc=error_inc
        )

        # --- 生成下一步回应 ---
        if phase == "IN_CLASS":
            # Pedagogy Agent 生成对应Level的提示
            ped = PedagogyAgent().run(req.message, context={
                "help_level": final_help_level, "knowledge_node": current_node
            })
            answer_parts.append(ped.answer)
            actual_agents_run.append({"name": "Pedagogy Agent", "task": f"Help L{final_help_level}提示生成", "status": "done"})

            # --- Socratic Tutor 引导式提问（调用智谱） ---
            soc = SocraticTutor().run(req.message, context={
                "knowledge_node": current_node,
                "help_level": final_help_level,
                "mastery": current_state["mastery"],
                "correctness": correctness,
                "error_type": eval_data.get("error_type", ""),
                "pedagogy_hint": ped.answer if 'ped' in dir() else "",
            })
            answer_parts.append("\n\n💡 " + soc.answer)
            actual_agents_run.append({"name": "Socratic Tutor", "task": f"生成L{final_help_level}引导提示（智谱）", "status": "done"})
            generation_source = soc.structured_data.get("generation_source", "local_fallback")

        elif phase == "PRE_CLASS":
            lp = LearningPathAgent().run(req.message, context={"weak_nodes": weak_nodes})
            answer_parts.append(f"📋 {diag.summary}\n\n🗺️ {lp.summary}")
            actual_agents_run.append({"name": "Learning Path Agent", "task": "规划预习路径", "status": "done"})

        elif phase == "POST_CLASS":
            answer_parts.append(f"📊 课堂回顾\n\n{diag.summary}")
            lp = LearningPathAgent().run(req.message, context={"weak_nodes": weak_nodes})
            answer_parts.append(f"\n\n{lp.summary}")
            actual_agents_run.append({"name": "Reflection Agent", "task": "课堂内容回顾", "status": "done"})

        else:
            # 通用问答
            know = KnowledgeAgent().run(req.message, context={"knowledge_node": current_node})
            answer_parts.append(know.answer)
            actual_agents_run.append({"name": "Knowledge Agent", "task": "知识点讲解", "status": "done"})

        # 保存上下文
        _chat_context[user_key] = ctx

        # 记录Agent运行日志
        db.log_agent_run(user["id"], req.session_id, "Orchestrator", orch_result.summary, phase, intent)
        for agent in actual_agents_run:
            db.log_agent_run(user["id"], req.session_id, agent["name"], agent["task"], phase, intent)

        return {
            "answer": "\n\n".join(answer_parts),
            "phase": phase,
            "intent": intent,
            "active_agents": [{"name": "Orchestrator", "task": "场景识别与路由", "status": "done"}] + actual_agents_run,
            "help_level": final_help_level,
            "knowledge_node": current_node,
            "generation_source": generation_source if 'generation_source' in dir() else "local_fallback",
            "evaluation": {
                "correctness": correctness,
                "score": eval_data["score"],
                "error_type": eval_data.get("error_type_desc", ""),
                "feedback": eval_data["feedback"],
            },
            "knowledge_updates": [{
                "node": current_node,
                "mastery_before": current_state["mastery"],
                "mastery_after": updated["mastery"],
                "mastery_delta": mastery_delta,
                "error_count": updated["error_count"],
                "status": updated["status"],
            }],
            "wrong_question_added": wrong_id is not None,
            "suggested_actions": ["查看知识图谱", "生成练习题", "查看学习路径"],
        }

    else:
        # ===== 教师端 =====
        if intent == "class_analysis":
            # 读取班级真实数据
            class_stats = db.get_class_avg_mastery(course_id)
            misconceptions = db.get_class_misconceptions(course_id)
            ca = ClassAnalyticsAgent().run(req.message, context={
                "class_stats": class_stats,
                "misconceptions": misconceptions,
            })
            answer_parts.append(f"📈 班级学情分析\n\n{ca.summary}")
            actual_agents_run.append({"name": "Class Analytics Agent", "task": "班级学情分析（基于真实DB数据）", "status": "done"})
            if misconceptions:
                actual_agents_run.append({"name": "Misconception Agent", "task": f"聚合{len(misconceptions)}类高频错因", "status": "done"})

        elif intent == "teaching_design":
            td = TeachingDesignAgent().run(req.message, context={"topic": req.message})
            answer_parts.append(td.answer)
            actual_agents_run.append({"name": "Teaching Design Agent", "task": "生成教学设计", "status": "done"})

        elif intent == "assessment":
            ass = AssessmentAgent().run(req.message, context={"topic": req.message})
            answer_parts.append(ass.answer)
            actual_agents_run.append({"name": "Assessment Agent", "task": "生成分层练习", "status": "done"})

        else:
            answer_parts.append("教师助手已就绪，请描述您需要的分析或教学任务。")

        # 记录日志
        db.log_agent_run(user["id"], req.session_id, "Orchestrator", orch_result.summary, phase, intent)
        for agent in actual_agents_run:
            db.log_agent_run(user["id"], req.session_id, agent["name"], agent["task"], phase, intent)

        return {
            "answer": "\n\n".join(answer_parts),
            "phase": phase,
            "intent": intent,
            "active_agents": [{"name": "Orchestrator", "task": "场景识别与路由", "status": "done"}] + actual_agents_run,
            "help_level": 0,
            "knowledge_node": None,
            "knowledge_updates": [],
        }


# ===== 学生端数据接口 =====
@router.get("/student/{username}/knowledge-graph")
async def get_student_knowledge_graph(username: str, course_name: str = "概率论与数理统计"):
    db = get_db()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    course_id = db.get_course_id_by_name(course_name)
    nodes = db.list_knowledge_nodes(course_id)
    edges = db.list_knowledge_edges(course_id)
    states = db.get_learner_state(user["id"], course_id)
    state_map = {s["node_id"]: s for s in states}

    graph_nodes = []
    for n in nodes:
        s = state_map.get(n["node_id"], {})
        graph_nodes.append({
            "id": n["node_id"],
            "name": n["name"],
            "chapter": n["chapter"],
            "description": n["description"],
            "bloom_level": n["bloom_level"],
            "mastery": s.get("mastery", 0),
            "status": s.get("status", "unlearned"),
            "error_count": s.get("error_count", 0),
            "common_misconception": n["common_misconception"],
        })

    return {"course": course_name, "is_demo": True, "data_source": "learner_states实时", "nodes": graph_nodes, "edges": edges}


@router.get("/student/{username}/learning-path")
async def get_learning_path(username: str, course_name: str = "概率论与数理统计"):
    db = get_db()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    course_id = db.get_course_id_by_name(course_name)
    path = db.get_learning_path(user["id"], course_id)
    nodes = {n["node_id"]: n for n in db.list_knowledge_nodes(course_id)}
    states = {s["node_id"]: s for s in db.get_learner_state(user["id"], course_id)}
    edges = db.list_knowledge_edges(course_id)

    # 构建前置关系图：node_id -> [prereq_ids]
    prereq_map = {}
    for e in edges:
        target = e["to_node"]
        source = e["from_node"]
        if target not in prereq_map:
            prereq_map[target] = []
        prereq_map[target].append(source)

    result = []
    for p in path:
        node = nodes.get(p["node_id"], {})
        state = states.get(p["node_id"], {})
        mastery = state.get("mastery", 0)
        # 根据mastery动态计算状态
        if mastery >= 0.8:
            dynamic_status = "completed"
        elif mastery >= 0.5:
            dynamic_status = "learning"
        elif mastery >= 0.3:
            dynamic_status = "current"
        else:
            dynamic_status = "weak"

        result.append({
            "node_id": p["node_id"],
            "name": node.get("name", p["node_id"]),
            "status": dynamic_status,
            "mastery": mastery,
            "sort_order": p["sort_order"],
            "needs_prereq": False,
        })

    # ===== 动态路径算法：综合mastery + 前置关系 =====
    # 1. 找到最薄弱的目标节点
    weak_nodes = sorted(result, key=lambda x: x["mastery"])
    target_node = weak_nodes[0] if weak_nodes else None

    # 2. 检查目标节点的前置节点是否需要复习
    if target_node:
        prereqs = prereq_map.get(target_node["node_id"], [])
        for prereq_id in prereqs:
            # 找前置节点在result中
            prereq_item = next((r for r in result if r["node_id"] == prereq_id), None)
            if prereq_item:
                prereq_mastery = prereq_item["mastery"]
                if prereq_mastery < 0.6:
                    # 前置薄弱，需要先复习
                    prereq_item["needs_prereq"] = True
                    prereq_item["status"] = "current"
                elif prereq_mastery >= 0.8:
                    # 前置已掌握，可以跳过
                    prereq_item["status"] = "completed"

    # 3. 排序优先级：
    # 0 = 需要前置复习的薄弱前置节点
    # 1 = 核心薄弱目标节点
    # 2 = 中等掌握
    # 3 = 已掌握
    def sort_key(x):
        if x.get("needs_prereq", False) and x["mastery"] < 0.6:
            return (0, x["mastery"])
        elif x["mastery"] < 0.3:
            return (1, x["mastery"])
        elif x["mastery"] >= 0.8:
            return (3, x["sort_order"])
        else:
            return (2, x["sort_order"])

    result.sort(key=sort_key)

    # 重新编号sort_order
    for i, item in enumerate(result):
        item["sort_order"] = i + 1

    return {"course": course_name, "is_demo": True,
            "data_source": "learner_states + knowledge_edges前置关系动态规划",
            "path": result}


@router.get("/student/{username}/wrong-book")
async def get_wrong_book(username: str, course_name: str = "概率论与数理统计"):
    db = get_db()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    course_id = db.get_course_id_by_name(course_name)
    wrongs = db.list_wrong_questions(user["id"], course_id)
    return {"course": course_name, "is_demo": True, "wrong_questions": wrongs, "total": len(wrongs)}


@router.post("/student/{username}/wrong-book/{wrong_id}/correct")
async def mark_wrong_corrected(username: str, wrong_id: int):
    """标记错题已订正"""
    db = get_db()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.mark_wrong_question_corrected(wrong_id)
    return {"status": "corrected", "wrong_id": wrong_id}


@router.get("/student/{username}/report")
async def get_student_report(username: str, course_name: str = "概率论与数理统计"):
    db = get_db()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    course_id = db.get_course_id_by_name(course_name)
    states = db.get_learner_state(user["id"], course_id)
    mastered = sum(1 for s in states if s["status"] == "mastered")
    learning = sum(1 for s in states if s["status"] == "learning")
    weak = sum(1 for s in states if s["status"] in ("weak", "unlearned"))
    avg_mastery = sum(s["mastery"] for s in states) / len(states) if states else 0

    return {
        "student": user["display_name"], "course": course_name, "is_demo": True,
        "summary_note": "趋势指标为演示数据，掌握度为实时计算",
        "overview": {"total_nodes": len(states), "mastered": mastered, "learning": learning, "weak": weak, "avg_mastery": round(avg_mastery, 2)},
        "weak_nodes": [{"node_id": s["node_id"], "mastery": s["mastery"]} for s in states if s["status"] in ("weak", "unlearned")][:5],
        "progress_trend": [0.2, 0.3, 0.35, 0.4, 0.45, round(avg_mastery, 2)],
    }


# ===== 教师端数据接口 =====
@router.get("/teacher/dashboard")
async def get_teacher_dashboard():
    db = get_db()
    course_id = db.get_course_id_by_name("概率论与数理统计")
    class_stats = db.get_class_avg_mastery(course_id)
    weak_topics_sorted = sorted(class_stats.items(), key=lambda x: x[1]["mastery"])[:5]
    weak_topics = [{"name": node, "mastery": round(stats["mastery"], 2), "error_count": stats["errors"]} for node, stats in weak_topics_sorted]
    all_mastery = [s["mastery"] for s in class_stats.values()]
    avg_mastery = sum(all_mastery) / len(all_mastery) if all_mastery else 0

    return {
        "course": "概率论与数理统计", "class_name": "2024级应用统计1班（演示）",
        "student_count": 5, "is_demo": True, "data_source": "learner_states实时聚合",
        "avg_mastery": round(avg_mastery, 2), "avg_accuracy": 0.65,
        "weak_topics": weak_topics, "at_risk_students": ["李四", "王五"],
        "weekly_trend": [0.45, 0.48, 0.5, 0.52, 0.51, round(avg_mastery, 2)],
    }


@router.get("/teacher/knowledge-graph")
async def get_class_knowledge_graph():
    db = get_db()
    course_id = db.get_course_id_by_name("概率论与数理统计")
    nodes = db.list_knowledge_nodes(course_id)
    edges = db.list_knowledge_edges(course_id)
    class_stats = db.get_class_avg_mastery(course_id)
    graph_nodes = [{
        "id": n["node_id"], "name": n["name"], "chapter": n["chapter"],
        "class_mastery": round(class_stats.get(n["node_id"], {"mastery": 0.3})["mastery"], 2),
        "high_error_students": max(1, int(class_stats.get(n["node_id"], {"errors": 1})["errors"])),
    } for n in nodes]
    return {"course": "概率论与数理统计", "is_demo": True, "data_source": "learner_states实时聚合", "nodes": graph_nodes, "edges": edges}


@router.get("/teacher/misconceptions")
async def get_misconceptions():
    """从wrong_questions实时聚合班级高频错因"""
    db = get_db()
    course_id = db.get_course_id_by_name("概率论与数理统计")
    data = db.get_class_misconceptions(course_id)

    if not data:
        return {"is_demo": True, "data_source": "wrong_questions表实时聚合", "misconceptions": [], "note": "暂无真实错题数据，以下为演示参考"}

    return {"is_demo": True, "data_source": "wrong_questions表实时聚合", "misconceptions": data}


@router.post("/teacher/design")
async def create_teaching_design(req: dict[str, str]):
    agent = TeachingDesignAgent()
    topic = req.get("topic", "假设检验")
    result = agent.run("", context={"topic": topic})
    return {"topic": topic, "is_demo": True, "design": result.answer,
            "active_agents": [{"name": "Teaching Design Agent", "task": f"生成《{topic}》教学设计", "status": "done"}]}


@router.post("/teacher/assessment")
async def create_assessment(req: dict[str, str]):
    agent = AssessmentAgent()
    topic = req.get("topic", "假设检验")
    result = agent.run("", context={"topic": topic})
    return {"topic": topic, "is_demo": True, "assessment": result.answer,
            "active_agents": [{"name": "Assessment Agent", "task": f"生成《{topic}》分层练习", "status": "done"}]}


# ===== AI知识图谱生成 =====
@router.post("/knowledge-graph/generate")
async def generate_knowledge_graph(req: dict[str, str]):
    """调用智谱LLM生成知识图谱，带JSON提取和重试"""
    topic = req.get("topic", "正态总体均值的假设检验")

    prompt = f"""请生成关于"{topic}"的知识图谱JSON。
只返回JSON格式，不要任何其他解释文字。
格式严格如下：
{{
  "nodes": [
    {{"id": "node_id", "name": "节点名称", "description": "简要描述"}}
  ],
  "edges": [
    {{"source": "前置节点id", "target": "后继节点id", "relation": "prerequisite"}}
  ]
}}
要求：
1. 至少包含8-12个核心知识点节点
2. 节点之间有合理的前置依赖关系
3. 只输出JSON，不要markdown代码块标记，不要解释"""

    try:
        from zhipu_client import ZhipuClient
        client = ZhipuClient()
        response = client.chat_once(
            [{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=1500
        )

        # 提取JSON（兼容markdown code block）
        import json
        import re

        # 尝试直接解析
        graph_data = None
        try:
            graph_data = json.loads(response)
        except json.JSONDecodeError:
            # 提取```json ... ``` 代码块
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if match:
                try:
                    graph_data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        # 第二次尝试：找第一个{到最后一个}
        if not graph_data:
            start = response.find('{')
            end = response.rfind('}')
            if start >= 0 and end > start:
                try:
                    graph_data = json.loads(response[start:end+1])
                except json.JSONDecodeError:
                    pass

        if graph_data and "nodes" in graph_data and "edges" in graph_data:
            return {
                "topic": topic,
                "is_demo": False,
                "source": "zhipu_llm",
                "nodes": graph_data["nodes"],
                "edges": graph_data["edges"],
            }
        else:
            # 解析失败，返回降级示例
            return {
                "topic": topic,
                "is_demo": True,
                "source": "template_fallback",
                "note": "LLM返回格式不符合要求，已降级为示例图谱",
                "nodes": [
                    {"id": "pop_mean", "name": "总体均值", "description": "研究对象的总体均值"},
                    {"id": "pop_var", "name": "总体方差", "description": "总体的离散程度"},
                    {"id": "sample_mean", "name": "样本均值", "description": "样本的平均值"},
                    {"id": "standard_error", "name": "标准误", "description": "样本均值的标准差"},
                    {"id": "z_test", "name": "Z检验", "description": "总体方差已知时的检验方法"},
                    {"id": "t_test", "name": "t检验", "description": "总体方差未知时的检验方法"},
                    {"id": "h0", "name": "原假设", "description": "待检验的假设"},
                    {"id": "alpha", "name": "显著性水平", "description": "犯第一类错误的概率"},
                ],
                "edges": [
                    {"source": "pop_mean", "target": "h0", "relation": "prerequisite"},
                    {"source": "pop_var", "target": "z_test", "relation": "prerequisite"},
                    {"source": "pop_var", "target": "t_test", "relation": "prerequisite"},
                    {"source": "sample_mean", "target": "standard_error", "relation": "prerequisite"},
                    {"source": "standard_error", "target": "z_test", "relation": "prerequisite"},
                    {"source": "standard_error", "target": "t_test", "relation": "prerequisite"},
                    {"source": "h0", "target": "alpha", "relation": "prerequisite"},
                ],
            }

    except Exception as e:
        return {
            "topic": topic,
            "is_demo": True,
            "source": "error_fallback",
            "note": f"AI服务暂时不可用，已使用本地示例: {str(e)[:50]}",
            "nodes": [],
            "edges": [],
        }


# ===== Demo一键重置 =====
@router.post("/demo/reset")
async def reset_demo_data():
    """一键重置演示数据到初始状态（仅Demo模式）"""
    import sqlite3
    conn = sqlite3.connect("data/meaita.db")
    try:
        # 清空运行时表
        conn.execute("DELETE FROM agent_runs")
        conn.execute("DELETE FROM wrong_questions")
        conn.execute("DELETE FROM learner_states")

        # 重新初始化演示数据
        from database import get_db
        db = get_db()
        db.init_demo_data()

        # 重新写入默认learner_states
        course_id = db.get_course_id_by_name("概率论与数理统计")
        nodes = db.list_knowledge_nodes(course_id)

        students = ["student001", "student002", "student003", "student004", "student005"]
        for i, stu in enumerate(students):
            user = db.get_user_by_username(stu)
            for j, node in enumerate(nodes):
                # 每个学生不同的初始掌握度
                base_mastery = 0.3 + 0.1 * ((i + j) % 4)
                conn.execute(
                    "INSERT INTO learner_states(user_id, course_id, node_id, mastery, bloom_level, error_count, status, last_updated) "
                    "VALUES(?,?,?,?,?,?,?,datetime('now'))",
                    (user["id"], course_id, node["node_id"],
                     round(base_mastery, 2), 1,
                     1 if base_mastery < 0.3 else 0,
                     "weak" if base_mastery < 0.3 else "learning")
                )
        conn.commit()
        return {"status": "ok", "message": "演示数据已重置", "tables_reset": ["learner_states", "wrong_questions", "agent_runs"]}
    finally:
        conn.close()
