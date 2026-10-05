# -*- coding: utf-8 -*-
"""ME-AITA 教师成长智能体 - 智谱大模型客户端

基于智谱官方 Python SDK（zhipuai）封装，统一管理：
- 模型调用（流式/非流式）
- 系统提示词注入
- 多轮上下文构建
- 错误分类与友好提示

官方文档：https://docs.bigmodel.cn/cn/guide/develop/python/introduction
"""
from __future__ import annotations

import logging
import os
from typing import Any, Iterator

from config import DEFAULT_BASE_URL, get_api_key, get_model

logger = logging.getLogger("meaita.zhipu")

# 统一的中文错误提示（不泄露内部细节）
ERROR_MESSAGES = {
    "auth": "API Key 无效或未授权（401）。请检查项目根目录 .env 或密钥文件中的 ZHIPU_API_KEY 是否正确。",
    "quota": "API 额度不足或账户余额不足（402/403）。请前往智谱开放平台检查账户额度。",
    "rate": "请求过于频繁，已被限流（429）。请稍等片刻后重试。",
    "model": "所配置的模型不可用或不存在。请在 .env 的 ZHIPU_MODEL 中更换模型（如 glm-4-flash / glm-4-plus）。",
    "timeout": "模型响应超时，请检查网络后重试。",
    "network": "无法连接智谱 API 服务器，请检查本机网络或代理设置。",
    "unknown": "模型服务暂时异常，请稍后重试。",
}


class ZhipuError(Exception):
    """携带用户可读信息的智谱调用异常。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ZhipuClient:
    """智谱 API 客户端封装。"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 120.0,
    ):
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            raise ZhipuError(
                "auth",
                "未检测到 ZHIPU_API_KEY。请在项目根目录 .env 中配置，或保留密钥文件（智谱API—key.txt）。",
            )
        self.model = model or get_model()
        self.base_url = base_url
        self.timeout = timeout
        self._client: Any = None

    def _ensure_client(self) -> Any:
        """惰性创建官方 SDK 客户端，避免模块导入阶段联网。"""
        if self._client is None:
            try:
                from zhipuai import ZhipuAI  # 官方 Python SDK

                self._client = ZhipuAI(
                    api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
                )
            except ImportError as exc:  # pragma: no cover
                raise ZhipuError(
                    "unknown",
                    "后端缺少 zhipuai 依赖，请在虚拟环境中执行 pip install -r requirements.txt。",
                ) from exc
        return self._client

    @staticmethod
    def classify(exc: Exception) -> ZhipuError:
        """把 SDK 异常映射为友好提示。"""
        name = type(exc).__name__
        text = str(exc)
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        code = getattr(exc, "code", None)

        if "AuthenticationError" in name or status == 401:
            return ZhipuError("auth", ERROR_MESSAGES["auth"])
        if (
            "Quota" in name
            or "Insufficient" in name
            or status in (402, 403)
            or "余额" in text
            or "额度" in text
            or "quota" in text.lower()
        ):
            return ZhipuError("quota", ERROR_MESSAGES["quota"])
        if "RateLimit" in name or status == 429:
            return ZhipuError("rate", ERROR_MESSAGES["rate"])
        if (
            "NotFound" in name
            or "Model" in name
            or status == 404
            or "model" in text.lower()
            or "模型" in text
        ):
            return ZhipuError("model", ERROR_MESSAGES["model"])
        if "Timeout" in name:
            return ZhipuError("timeout", ERROR_MESSAGES["timeout"])
        if (
            "Connection" in name
            or "ConnectError" in name
            or "APIConnection" in name
            or "网络" in text
        ):
            return ZhipuError("network", ERROR_MESSAGES["network"])
        # 其他 APIStatusError / ZhipuAIError
        logger.warning("智谱调用异常: %s %s %s", name, status, code)
        return ZhipuError("unknown", ERROR_MESSAGES["unknown"])

    def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict] | None = None,
    ) -> Iterator[str]:
        """流式对话：逐段产出文本。"""
        client = self._ensure_client()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        try:
            stream = client.chat.completions.create(**payload)
        except Exception as exc:  # noqa: BLE001
            raise self.classify(exc) from exc

        try:
            for chunk in stream:
                try:
                    choices = getattr(chunk, "choices", None)
                    if not choices:
                        continue
                    delta = choices[0].delta
                    content = getattr(delta, "content", None)
                    if content:
                        yield content
                except Exception:  # noqa: BLE001
                    continue
        except Exception as exc:  # noqa: BLE001
            raise self.classify(exc) from exc

    def chat_once(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """非流式对话（用于单次测试/辅助任务）。"""
        client = self._ensure_client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            raise self.classify(exc) from exc

    def available(self) -> bool:
        """健康检查：确认 API Key 与模型可用（非流式极简请求）。"""
        try:
            reply = self.chat_once(
                [{"role": "user", "content": "请只回复两个字：正常"}], max_tokens=16
            )
            return bool(reply)
        except ZhipuError as exc:
            logger.warning("智谱可用性检查失败: %s", exc.code)
            return False


# 供测试注入环境变量用
def _reset_env(env: dict[str, str]) -> None:  # pragma: no cover
    for k, v in env.items():
        os.environ[k] = v
