# -*- coding: utf-8 -*-
"""ME-AITA 教师成长智能体 - 后端配置模块

安全说明：
- API Key 只通过环境变量 / .env / 项目根目录的密钥文件读取，绝不写入前端资源或日志。
- 本模块不会在任何输出中打印完整密钥。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录：backend/ 的上一级
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 加载项目根目录下的 .env（若存在）
load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8")

DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "meaita.db"
RESOURCES_JSON = DATA_DIR / "resources.json"
LOG_FILE = LOG_DIR / "backend.log"

DEFAULT_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")
DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# 允许用户在 .env 中配置的模型（文档中确认可用的 GLM 系列）
SUPPORTED_MODELS = [
    "glm-4-flash",
    "glm-4-flash-250414",
    "glm-4-air",
    "glm-4-air-250414",
    "glm-4-plus",
    "glm-4.7",
]


def _read_key_file() -> str | None:
    """从项目根目录的密钥文件中读取 API Key（兼容用户提供的文件名）。"""
    candidates = [
        PROJECT_ROOT / "智谱API—key.txt",
        PROJECT_ROOT / "智谱API-key.txt",
        PROJECT_ROOT / "zhipu_api_key.txt",
        PROJECT_ROOT / "api_key.txt",
    ]
    # 兜底：通配匹配“智谱API*key*.txt”
    for pattern in ("智谱API*key*.txt", "*api*key*.txt", "zhipu*key*.txt"):
        try:
            candidates.extend(sorted(PROJECT_ROOT.glob(pattern)))
        except OSError:
            pass
    for path in candidates:
        try:
            if path.is_file():
                content = path.read_text(encoding="utf-8-sig").strip()
                if content and re.fullmatch(r"[\w.\-]+", content):
                    return content
        except OSError:
            continue
    return None


def get_api_key() -> str | None:
    """按优先级返回 API Key：环境变量 ZHIPU_API_KEY > .env > 密钥文件。

    返回值仅用于创建客户端，绝不写入日志。
    """
    key = os.getenv("ZHIPU_API_KEY")
    if key and key.strip():
        return key.strip()
    key = _read_key_file()
    if key:
        return key
    return None


def mask_key(key: str | None) -> str:
    """对密钥做脱敏展示（仅用于日志中标识是否已配置）。"""
    if not key:
        return "<未配置>"
    if len(key) <= 8:
        return "<已配置>"
    return f"{key[:4]}****{key[-4:]}"


def get_model() -> str:
    model = os.getenv("ZHIPU_MODEL", DEFAULT_MODEL).strip()
    return model or DEFAULT_MODEL
