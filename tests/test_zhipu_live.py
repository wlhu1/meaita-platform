# -*- coding: utf-8 -*-
"""智谱 API 连通性测试：使用项目根目录密钥文件，绝不打印密钥。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from zhipu_client import ZhipuClient  # noqa: E402


def main() -> None:
    try:
        client = ZhipuClient(model="glm-4-flash")
    except Exception as exc:  # noqa: BLE001
        print(f"[密钥加载失败] {exc}")
        return
    print(f"使用模型: {client.model}")
    try:
        reply = client.chat_once(
            [
                {"role": "system", "content": "你是河南大学ME-AITA教师成长智能体，请简要回答。"},
                {"role": "user", "content": "你好，请用一句话介绍你自己。"},
            ],
            max_tokens=128,
        )
        print(f"[真实模型返回] {reply}")
    except Exception as exc:  # noqa: BLE001
        print(f"[调用失败] {exc}")


if __name__ == "__main__":
    main()
