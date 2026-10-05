# ME-AITA 教师成长智能体 — 公网部署说明

## 公网地址
- 生产域名：https://meaita-teacher.pages.dev/
- 项目名：meaita-teacher（Cloudflare Pages）

## 技术架构
- 前端：原生 HTML/CSS/JS，部署在 Cloudflare Pages 静态资源。
- 后端：Cloudflare Pages Functions（Workers 运行时，TypeScript），文件 `frontend/functions/api/[[route]].ts`。
- 数据库：Cloudflare D1（SQLite 兼容），绑定名 `DB`，数据库名 `meaita-teacher-db`。
- 大模型：智谱 GLM-4-Flash，OpenAI 兼容接口 `https://open.bigmodel.cn/api/paas/v4/chat/completions`，服务端 fetch 直连。
- API Key 与模型名通过 Cloudflare Secrets 管理，不落入任何前端文件。

## 已部署功能
- 智能问答（SSE 流式、多轮会话、Markdown 渲染）
- 会话管理（新建/历史/删除/自动重命名）
- 数字素养诊断（15 题试用版，五维度）
- 优质资源推荐（按学段/学科/类别检索）
- 教师社区（轻量发帖列表，由后端 API 提供）
- 首页河大校园版视觉（大门背景、浅蓝白配色、紧凑三卡片）

## 安全
- `ZHIPU_API_KEY`、`ZHIPU_MODEL` 通过 `wrangler pages secret put` 注入，浏览器不可见。
- 前端代码中无密钥、无 localhost 地址。
- 注意：当前为开放演示版，未做用户登录/权限隔离；如需公网长期使用，应增加身份认证与限流。

## 本地开发
- 本地仍可使用 Python FastAPI 后端（`venv\Scripts\python.exe backend\main.py`），监听 127.0.0.1:8000。
- 前端文件位于 `frontend/`。

## 更新部署
```powershell
cd D:\EDGE\基础教育智能体\frontend
npx wrangler pages deploy . --project-name meaita-teacher
```
修改 Functions（`functions/api/[[route]].ts`）后必须重新执行上述命令。

## 查看实时日志
```powershell
cd D:\EDGE\基础教育智能体\frontend
npx wrangler pages deployment tail --project-name meaita-teacher
```

## 常见操作
- 查看 secrets：`npx wrangler pages secret list --project-name meaita-teacher`
- 重置模型：`"glm-4-flash" | npx wrangler pages secret put ZHIPU_MODEL --project-name meaita-teacher`
- 重置密钥：`Get-Content "..\智谱API—key.txt" | npx wrangler pages secret put ZHIPU_API_KEY --project-name meaita-teacher`

## 不影响的项目
- https://matheff-agent.pages.dev/ 是另一独立 Pages 项目，本次部署未触碰其任何配置、D1 或 Secrets。
