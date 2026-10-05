# -*- coding: utf-8 -*-
"""ME-AITA 数字素养诊断引擎（试用版）

依据《教师数字素养》教育行业标准（JY/T 0646—2022）的五个一级维度设计：
数字意识、数字技术知识与技能、数字化教学应用、数字化专业发展、数字社会责任。

说明：
- 本测评为“试用版”基础测评，用于能力画像与自学参考，并非经过验证的正式能力评价。
- 评分与建议由确定性规则计算，不由大模型生成，避免无依据的能力分数。
"""
from __future__ import annotations

DIMENSIONS = [
    "数字意识",
    "数字技术知识与技能",
    "数字化教学应用",
    "数字化专业发展",
    "数字社会责任",
]

# 每个维度 3 题，共 15 题；选项 1-5（1=非常不符合 … 5=非常符合）
QUESTION_BANK: list[dict] = [
    # 数字意识
    {"id": "d1q1", "dimension": "数字意识", "text": "我能认识到数字技术对教学改革和自身专业发展的重要性。"},
    {"id": "d1q2", "dimension": "数字意识", "text": "我主动关注国家教育数字化战略与基础教育信息化相关政策动态。"},
    {"id": "d1q3", "dimension": "数字意识", "text": "面对新的数字工具和教学方式，我愿意主动了解并尝试。"},
    # 数字技术知识与技能
    {"id": "d2q1", "dimension": "数字技术知识与技能", "text": "我能熟练使用办公软件（文档、表格、演示）处理教学材料。"},
    {"id": "d2q2", "dimension": "数字技术知识与技能", "text": "我能独立完成教学资源的检索、下载、整理与二次编辑。"},
    {"id": "d2q3", "dimension": "数字技术知识与技能", "text": "我能理解并初步运用人工智能工具（如生成式AI）辅助备课与教学。"},
    # 数字化教学应用
    {"id": "d3q1", "dimension": "数字化教学应用", "text": "我能使用多媒体和互动工具设计并实施数字化课堂活动。"},
    {"id": "d3q2", "dimension": "数字化教学应用", "text": "我能利用平台或工具开展学情分析、作业布置与学习反馈。"},
    {"id": "d3q3", "dimension": "数字化教学应用", "text": "我能借助数字手段关注学生差异，进行分层或个性化教学调整。"},
    # 数字化专业发展
    {"id": "d4q1", "dimension": "数字化专业发展", "text": "我会利用网络研修平台、在线课程持续学习提升。"},
    {"id": "d4q2", "dimension": "数字化专业发展", "text": "我能借助数字工具开展课例研究、听评课与教学反思。"},
    {"id": "d4q3", "dimension": "数字化专业发展", "text": "我乐于在教研组或网络社群中分享数字教学经验并协作共创。"},
    # 数字社会责任
    {"id": "d5q1", "dimension": "数字社会责任", "text": "我了解并遵守信息安全、数据隐私与网络伦理规范。"},
    {"id": "d5q2", "dimension": "数字社会责任", "text": "我注重引导学生正确、安全、健康地使用数字设备和网络。"},
    {"id": "d5q3", "dimension": "数字社会责任", "text": "我能辨别网络信息真伪，并重视在教学中渗透数字公民教育。"},
]

# 身份 / 学段 / 学科 选项
IDENTITIES = ["师范生", "在职教师", "教研员", "教育管理者", "其他"]
STAGES = ["小学", "初中", "高中", "其他"]
SUBJECTS = [
    "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理",
    "道德与法治", "科学", "信息技术", "体育与健康", "音乐", "美术", "通用", "其他",
]

# 每维度建议（按得分率分档）
DIMENSION_SUGGESTIONS: dict[str, dict[str, str]] = {
    "数字意识": {
        "high": "数字意识较强。建议保持对教育数字化政策的持续关注，并将意识转化为具体的课堂实践行动，如每学期完成1个数字化教学设计。",
        "mid": "已有一定数字意识。建议定期阅读教育数字化政策与案例（如教育部官网、国家中小学智慧教育平台教师研修栏目），尝试将AI工具引入一次真实教学环节。",
        "low": "数字意识有待提升。建议从了解《教师数字素养》标准与教育数字化战略开始，先关注1-2个可靠的官方信息渠道，逐步建立对数字技术的价值认知。",
    },
    "数字技术知识与技能": {
        "high": "数字技术基础扎实。建议进一步学习数据可视化、AI提示词工程等进阶技能，并输出可分享的实操经验。",
        "mid": "具备一定技术基础。建议重点练习教学资源的检索与二次编辑、AI工具辅助备课，形成个人资源素材库。",
        "low": "数字技术技能需要加强。建议从办公软件与资源检索入手，通过国家中小学智慧教育平台的研修课程进行系统训练。",
    },
    "数字化教学应用": {
        "high": "数字化教学应用能力突出。建议尝试常态化应用并开展效果对比研究，形成可推广的教学案例。",
        "mid": "已有数字化教学应用尝试。建议针对学情分析、作业反馈和个性化调整三个环节各做一次专项优化。",
        "low": "数字化教学应用尚少。建议从单节课的互动工具（如问卷星、课堂互动白板）入手，小步快跑积累经验。",
    },
    "数字化专业发展": {
        "high": "数字化专业发展意识强。建议将分散的网络学习整合为系统研修计划，并承担校本研修的分享任务。",
        "mid": "有一定研修习惯。建议利用平台研修课程完成专题学习，并用数字工具记录课例研究过程。",
        "low": "数字化研修参与不足。建议先从网络研修平台的免费课程开始，每周固定1-2小时线上学习时间。",
    },
    "数字社会责任": {
        "high": "数字社会责任意识强。建议在教研组或班级中主动开展网络安全与数字伦理教育实践。",
        "mid": "具备基本责任意识。建议系统学习《数据安全法》《未成年人保护法》网络保护相关要求，完善课堂中的数字公民教育。",
        "low": "数字社会责任意识需要提升。建议学习信息安全基础知识和未成年人网络保护要求，并在教学中增加相关内容。",
    },
}


def _clamp(value: int, lo: int = 1, hi: int = 5) -> int:
    return max(lo, min(hi, int(value)))


def compute_scores(answers: dict) -> dict:
    """按维度汇总得分（每维度 3 题 × 1-5 分，维度分 3-15，总分 15-75）。"""
    scores = {d: 0 for d in DIMENSIONS}
    counts = {d: 0 for d in DIMENSIONS}
    for q in QUESTION_BANK:
        dim = q["dimension"]
        val = answers.get(q["id"])
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()):
            scores[dim] += _clamp(int(val))
            counts[dim] += 1
    # 未作答的维度按最低分处理（保证可计算），并标记
    missing = {d: (3 - counts[d]) for d in DIMENSIONS}
    for d, m in missing.items():
        scores[d] += m * 1
    total = sum(scores.values())
    return {"scores": scores, "total": total, "missing": missing}


def get_level(total: int) -> str:
    if total >= 60:
        return "优秀"
    if total >= 48:
        return "良好"
    if total >= 36:
        return "基础"
    return "待提升"


def build_report(answers: dict) -> dict:
    """计算得分并生成报告（确定性规则，标注试用版）。"""
    result = compute_scores(answers)
    scores = result["scores"]
    total = result["total"]
    level = get_level(total)

    dim_reports = []
    for d in DIMENSIONS:
        score = scores[d]
        ratio = score / 15.0
        if ratio >= 0.8:
            band = "high"
            band_label = "较强"
        elif ratio >= 0.55:
            band = "mid"
            band_label = "中等"
        else:
            band = "low"
            band_label = "待提升"
        dim_reports.append(
            {
                "dimension": d,
                "score": score,
                "max": 15,
                "ratio": round(ratio, 2),
                "band": band_label,
                "suggestion": DIMENSION_SUGGESTIONS[d][band],
            }
        )

    # 总体建议
    overall = {
        "优秀": "整体数字素养水平较高。建议发挥示范作用，将数字化经验系统化输出（如形成案例、承担校本研修主讲），并关注生成式AI等前沿工具在教学中的深度应用。",
        "良好": "整体数字素养良好。建议对照《教师数字素养》标准查漏补缺，优先提升得分最低的维度，制定3个月的可执行提升计划。",
        "基础": "已具备一定数字素养基础。建议从得分最低的两个维度入手，借助国家中小学智慧教育平台等官方渠道完成系统学习，每2周实践一个数字化教学小技巧。",
        "待提升": "数字素养提升空间较大。建议先建立学习计划：了解《教师数字素养》标准 → 完成基础技术技能训练 → 尝试1-2个数字化课堂应用，循序渐进。",
    }[level]

    return {
        "trial_note": "本报告为试用版基础测评结果，用于能力画像与自学参考，非正式能力评价。",
        "scores": scores,
        "total": total,
        "max_total": 75,
        "level": level,
        "dimensions": dim_reports,
        "overall_suggestion": overall,
    }
