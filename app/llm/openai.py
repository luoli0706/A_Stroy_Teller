import asyncio
from typing import Callable, Optional

from langchain_openai import ChatOpenAI

from app.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    DEFAULT_TEMPERATURE,
)
from app.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API LLM Provider。"""

    def __init__(
        self,
        api_key: str = OPENAI_API_KEY,
        base_url: str = OPENAI_BASE_URL,
        default_temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY 未设置，无法初始化 OpenAI Provider。")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_temperature = default_temperature

    async def health_check_async(self) -> dict:
        try:
            llm = ChatOpenAI(
                model="gpt-4o",
                api_key=self.api_key,
                base_url=self.base_url,
                temperature=0.0,
                max_tokens=1,
            )
            await llm.ainvoke("ping")
            return {"ok": True, "message": "OpenAI 健康检查通过。"}
        except Exception as e:
            return {"ok": False, "message": f"OpenAI 连接失败: {str(e)}"}

    def assert_ready(self) -> None:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY 未设置。")
        # 不在此处做同步健康检查，避免与新事件循环冲突

    async def chat_async(
        self,
        model: str,
        prompt: str,
        temperature: float,
        token_callback: Optional[Callable[[dict], None]] = None,
        event_meta: Optional[dict] = None,
        response_format: Optional[str] = None,
    ) -> str:
        temp = self.default_temperature if temperature is None else temperature

        kwargs = dict(
            model=model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=float(temp),
        )

        if response_format == "json":
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}

        llm = ChatOpenAI(**kwargs)

        if token_callback:
            parts: list[str] = []
            meta = event_meta or {}
            async for chunk in llm.astream(prompt):
                content = getattr(chunk, "content", "")
                text = str(content) if not isinstance(content, list) else "".join(map(str, content))
                if text:
                    parts.append(text)
                    token_callback({
                        "event": "token",
                        "node": meta.get("node", ""),
                        "model": model,
                        "role_id": meta.get("role_id", ""),
                        "text": text,
                    })
            return "".join(parts).strip()

        response = await llm.ainvoke(prompt)
        content = getattr(response, "content", "")
        return str(content).strip() if not isinstance(content, list) else "\n".join(map(str, content)).strip()
