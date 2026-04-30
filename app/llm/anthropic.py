import asyncio
from typing import Callable, Optional

from langchain_anthropic import ChatAnthropic

from app.config import (
    ANTHROPIC_API_KEY,
    DEFAULT_TEMPERATURE,
)
from app.llm.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API LLM Provider。

    注意：Anthropic 不支持原生 JSON mode。
    当 response_format="json" 时，会在 prompt 中追加 JSON 输出指令。
    """

    def __init__(
        self,
        api_key: str = ANTHROPIC_API_KEY,
        default_temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 未设置，无法初始化 Anthropic Provider。")
        self.api_key = api_key
        self.default_temperature = default_temperature

    async def health_check_async(self) -> dict:
        try:
            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=self.api_key,
                temperature=0.0,
                max_tokens=1,
            )
            await llm.ainvoke("ping")
            return {"ok": True, "message": "Anthropic 健康检查通过。"}
        except Exception as e:
            return {"ok": False, "message": f"Anthropic 连接失败: {str(e)}"}

    def assert_ready(self) -> None:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 未设置。")

    def _add_json_instruction(self, prompt: str) -> str:
        """Anthropic 无原生 JSON mode，在 prompt 尾部追加约束。"""
        if "Respond with a JSON object" in prompt or "Return a JSON" in prompt:
            return (
                prompt
                + "\n\nIMPORTANT: You must respond with a valid JSON object only. "
                "No markdown, no code fences, no explanation — just the raw JSON."
            )
        return prompt

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

        if response_format == "json":
            prompt = self._add_json_instruction(prompt)

        llm = ChatAnthropic(
            model=model,
            api_key=self.api_key,
            temperature=float(temp),
        )

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
