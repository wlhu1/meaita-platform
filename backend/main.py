# -*- coding: utf-8 -*-
"""ME-AITA 教师成长智能体 - FastAPI 后端入口

启动：python backend/main.py  （或使用项目根目录 启动智能体.bat）
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import FRONTEND_DIR, LOG_DIR, LOG_FILE, get_api_key, get_model, mask_key
from routers import chat, diagnosis, resources, community
from routers import multi_agent

# ---------- 日志（不记录任何密钥） ----------
LOG_DIR.mkdir(parents=True, exist_ok=True)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)
# 抑制过噪第三方日志
for noisy in ("uvicorn.access", "httpx", "httpcore"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("meaita.main")

app = FastAPI(
    title="ME-AITA 教师成长智能体",
    version="1.0.0",
    description="河南大学面向基础教育教师的专业发展智能体（本地部署版）",
)

# 允许本地 file:// 直接打开前端页面时也能调用后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(diagnosis.router)
app.include_router(resources.router)
app.include_router(community.router)
app.include_router(multi_agent.router)


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/index.html")
def index_html():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/diagnosis.html")
def diagnosis_page():
    return FileResponse(FRONTEND_DIR / "diagnosis.html")


@app.get("/resources.html")
def resources_page():
    return FileResponse(FRONTEND_DIR / "resources.html")


@app.get("/community.html")
def community_page():
    return FileResponse(FRONTEND_DIR / "community.html")


@app.get("/about.html")
def about_page():
    return FileResponse(FRONTEND_DIR / "about.html")


@app.get("/student")
def student_page():
    return FileResponse(FRONTEND_DIR / "student.html")


@app.get("/teacher")
def teacher_page():
    return FileResponse(FRONTEND_DIR / "teacher.html")


# 静态资源（css/js/vendor/assets）
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# 首页 index.html 内相对路径资源（css/ js/ vendor/ assets/）也能访问
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/vendor", StaticFiles(directory=FRONTEND_DIR / "vendor"), name="vendor")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/api/info")
def info():
    """前端可见的后端/模型信息（不含密钥）。"""
    return {
        "service": "ME-AITA 教师成长智能体",
        "model": get_model(),
        "api_configured": bool(get_api_key()),
        "api_key_masked": mask_key(get_api_key()),
        "version": "1.0.0",
    }


def main() -> None:
    import uvicorn
    import os

    key_state = "已配置" if get_api_key() else "未配置（请检查 .env 或密钥文件）"
    logger.info("ME-AITA 后端启动，模型=%s，API Key：%s", get_model(), key_state)
    print("=" * 56)
    print("  ME-AITA 教师成长智能体")
    print(f"  模型: {get_model()}   API Key: {key_state}")
    print("=" * 56)
    # 云平台（Render/Railway等）通过环境变量指定 host/port
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
