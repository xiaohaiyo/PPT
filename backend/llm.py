from __future__ import annotations

import asyncio
import base64
import json
import re
import urllib.request
from typing import Any

from .config import settings


class LLMProvider:
    """OpenAI-compatible provider. The SDK is imported only when configured."""

    def __init__(self) -> None:
        self.enabled = settings.llm_ready
        self._client = None
        if self.enabled:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.api_key, base_url=settings.base_url, timeout=settings.llm_timeout, max_retries=0)

    async def json(self, system: str, user: str) -> dict[str, Any]:
        if not self.enabled or self._client is None:
            raise RuntimeError("LLM 未配置")

        def request():
            return self._client.chat.completions.create(
                model=settings.model,
                messages=[
                    {"role": "system", "content": system + "\n只输出合法 JSON，不要输出 Markdown 代码块。"},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )

        response = await asyncio.to_thread(request)
        text = response.choices[0].message.content or "{}"
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("模型未返回 JSON")
        return json.loads(match.group(0))

    async def text(self, system: str, user: str) -> str:
        if not self.enabled or self._client is None:
            raise RuntimeError("LLM 未配置")

        def request():
            return self._client.chat.completions.create(
                model=settings.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.3,
            )

        response = await asyncio.to_thread(request)
        return response.choices[0].message.content or ""

    @property
    def image_enabled(self) -> bool:
        return bool(self._client is not None and settings.image_model)

    async def image(self, prompt: str) -> bytes:
        if not self.image_enabled:
            raise RuntimeError("图片模型未配置")

        def request() -> bytes:
            response = self._client.images.generate(model=settings.image_model, prompt=prompt, size="1024x1024", n=1)
            item = response.data[0]
            if getattr(item, "b64_json", None):
                return base64.b64decode(item.b64_json)
            if getattr(item, "url", None):
                with urllib.request.urlopen(item.url, timeout=30) as remote:
                    return remote.read(15 * 1024 * 1024)
            raise ValueError("图片模型没有返回图片数据")

        return await asyncio.to_thread(request)


provider = LLMProvider()
