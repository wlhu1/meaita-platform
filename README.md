# ME-AITA 多智能体智慧教学平台（河南大学）

AI驱动课前·课中·课后全过程精准教学。面向基础教育的多智能体协同教学系统，包含学生端个性化学习和教师端教学决策支持。

> **版本：** v2.0.0 多智能体扩展版
> **演示课程：** 概率论与数理统计

---

## 功能概览

### 🎓 学生端

- **AI学习伙伴**：多智能体协同答疑，Help Ladder分级引导（L1反思→L5完整讲解）
- **知识图谱**：ECharts可交互图谱，节点状态可视化（已掌握/学习中/薄弱/未学习）
- **学习路径**：个性化学习路径规划，AI重新规划
- **错题档案**：错题记录、错因分析、与AI联动
- **成长报告**：掌握度概览、薄弱点分析、AI学习建议

### 👩‍🏫 教师端

- **班级总览Dashboard**：平均掌握度、正确率、薄弱知识点TOP5、待关注学生
- **班级知识图谱**：班级整体掌握率可视化，点击查看详情
- **高频错因**：预置典型错误模式，AI深度分析
- **AI教学设计**：输入知识点自动生成完整教案（目标/重难点/问题链/分层任务）
- **分层练习生成**：基础组/提高组/挑战组三层练习

### 🤖 多智能体架构

| Agent | 职责 |
|-------|------|
| Orchestrator | 场景识别（课前/课中/课后）与Agent路由 |
| Diagnosis Agent | 学习诊断与薄弱点分析 |
| Pedagogy Agent | Help Ladder教学策略 |
| Socratic Tutor | 苏格拉底式引导提问 |
| Knowledge Agent | 知识点系统讲解 |
| Learning Path Agent | 个性化学习路径规划 |
| Class Analytics Agent | 班级学情分析 |
| Misconception Agent | 高频错因识别 |
| Teaching Design Agent | AI教学设计生成 |
| Assessment Agent | 分层练习生成 |

---

## 快速启动

```bash
# 启动后端
venv\Scripts\python.exe backend\main.py

# 访问
# 总首页: http://127.0.0.1:8000
# 学生端: http://127.0.0.1:8000/student?user=student001
# 教师端: http://127.0.0.1:8000/teacher
```

---

## 演示账号

| 角色 | 账号 | 说明 |
|------|------|------|
| 学生 | student001 | 张三（主演示账号，学习到t检验） |
| 学生 | student002 | 李四（进度较慢） |
| 教师 | teacher001 | 王老师 |

---

## 技术栈

- **后端：** FastAPI + SQLite
- **前端：** 原生HTML/CSS/JS + ECharts
- **AI：** 智谱GLM-4-Flash（真实接入）
- **部署：** 本地单机运行

---

## 安全说明

- API Key仅存于服务器环境变量，前端无泄漏
- 所有LLM请求经由后端转发，Key不暴露给浏览器
- 演示数据明确标注"演示课程数据"

---

详细测试报告请查看 [TEST_REPORT.md](./TEST_REPORT.md)
