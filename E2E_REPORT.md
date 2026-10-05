# ME-AITA 多智能体智慧教学平台 — 端到端(E2E)测试报告

**测试日期**: 2026-10-03  
**测试环境**: Windows / Python 3.11 / SQLite / 智谱GLM-4-Flash  
**测试账号**: student001 / teacher001

---

## 一、E2E测试流程与结果

| # | 测试步骤 | 请求 | 验证点 | 结果 |
|---|----------|------|--------|------|
| 1 | 重置演示环境 | `POST /api/demo/reset` | 返回status=ok，清空learner_states/wrong_questions/agent_runs | ✅ PASS |
| 2 | 学生登录查看初始状态 | `GET /api/student/student001/knowledge-graph` | 返回16个节点，mastery从DB读取 | ✅ PASS |
| 3 | 学生发送错误答案 | `POST /api/agent/chat` (role=student) | Evaluation=incorrect/partially_correct | ✅ PASS |
| 4 | 错题自动入库 | 检查wrong_questions表 | 新增1条记录，包含error_type/help_level | ✅ PASS |
| 5 | learner_states更新 | 对比前后mastery | mastery发生变化（±0.01~0.08） | ✅ PASS |
| 6 | Help Level变化 | 查看返回help_level | 答错后Help Level升高 | ✅ PASS |
| 7 | 学生再次正确回答 | `POST /api/agent/chat` | Evaluation=correct，mastery上升 | ✅ PASS |
| 8 | 知识图谱同步 | `GET /api/student/student001/knowledge-graph` | 对应节点mastery已更新 | ✅ PASS |
| 9 | 学习路径动态重排序 | `GET /api/student/student001/learning-path` | 最薄弱节点排最前 | ✅ PASS |
| 10 | 教师Dashboard数据 | `GET /api/teacher/dashboard` | avg_mastery从learner_states聚合计算 | ✅ PASS |
| 11 | 高频错因变化 | `GET /api/teacher/misconceptions` | 学生答错后count增加 | ✅ PASS |
| 12 | 教师AI分析 | `POST /api/agent/chat` (role=teacher) | ClassAnalyticsAgent调用智谱生成分析 | ✅ PASS |
| 13 | AI教学设计 | `POST /api/teacher/design` | 真实调用智谱，返回结构化教案 | ✅ PASS |
| 14 | 分层练习生成 | `POST /api/teacher/assessment` | 真实调用智谱，三层题目 | ⚠️ 偶发超时 |
| 15 | AI知识图谱生成 | `POST /api/knowledge-graph/generate` | 12节点15边，真实调用智谱 | ✅ PASS |
| 16 | Agent日志记录 | 查询agent_runs表 | 每次对话记录所有执行Agent | ✅ PASS |

---

## 二、响应性能测试

| 接口 | 平均响应时间 | 备注 |
|------|-------------|------|
| 学生聊天（规则路由） | 0.3~0.8秒 | 无LLM调用 |
| 教师AI分析 | 3~8秒 | 1次智谱调用 |
| AI教学设计 | 5~12秒 | 1次智谱调用 |
| 分层练习生成 | 8~15秒 | 1次智谱调用，偶发超时 |
| AI知识图谱生成 | 10~20秒 | 1次智谱调用，输出较长 |
| Demo Reset | <0.5秒 | 纯数据库操作 |

**结论**: 学生聊天路由全规则化，响应快；LLM调用集中在教师端和生成类功能，符合设计预期。

---

## 三、异常降级测试

| 异常场景 | 系统行为 | 结果 |
|----------|----------|------|
| 智谱API Key错误 | 自动降级为模板，明确标注"本地降级方案" | ✅ 正常 |
| 智谱API超时 | 降级模板，不崩溃 | ✅ 正常 |
| LLM返回非JSON格式 | 自动提取code block → 截取{到} → 重试一次 → 最终降级示例 | ✅ 正常 |
| 学生不存在 | 返回404错误 | ✅ 正常 |
| 空消息 | 返回友好提示 | ✅ 正常 |

---

## 四、LLM调用成本审计

| 场景 | LLM调用次数 | 说明 |
|------|------------|------|
| 学生普通提问 | 0次 | Orchestrator规则路由，Evaluation规则评价 |
| 学生答错后引导 | 0次 | Pedagogy/Socratic模板生成 |
| 教师班级分析 | 1次 | 数据本地聚合，LLM只负责自然语言生成 |
| AI教学设计 | 1次 | 直接生成教案 |
| 分层练习生成 | 1次 | 直接生成题目 |
| AI知识图谱生成 | 1次 | 直接生成JSON |

**结论**: 普通学习问答0次LLM调用，控制成本；仅教师端生成类功能调用LLM，符合"规则路由+按需LLM"架构原则。

---

## 五、测试总结

**总通过率**: 15/16 = 93.75%  
**核心闭环全部PASS**：学生答错→Evaluation→错题入库→mastery更新→图谱同步→教师Dashboard同步→高频错因变化

**唯一已知问题**: 练习生成偶发超时（智谱响应慢），已有模板降级，不影响演示。

---

**测试结论**: 系统达到比赛演示要求，数据闭环完整，LLM调用真实，异常降级健全。
