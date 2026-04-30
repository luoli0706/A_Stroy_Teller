import asyncio
from typing import Callable, Optional

import httpx
from langchain_ollama import ChatOllama

from app.config import OLLAMA_BASE_URL, DEFAULT_TEMPERATURE
from app.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Ollama 本地 LLM Provider。"""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        default_temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_temperature = default_temperature

    async def _list_models_async(self) -> list[str]:
        tags_url = f"{self.base_url}/api/tags"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(tags_url, timeout=5.0)
                response.raise_for_status()
                payload = response.json()
                return [str(m.get("model", "")).strip() for m in payload.get("models", [])]
            except Exception:
                return []

    @staticmethod
    def _model_aliases(model_name: str) -> set[str]:
        value = model_name.strip()
        aliases = {value}
        if value.endswith(":latest"):
            aliases.add(value[: -len(":latest")])
        elif ":" not in value:
            aliases.add(f"{value}:latest")
        return aliases

    async def health_check_async(self) -> dict:
        available_models = await self._list_models_async()
        if not available_models:
            return {"ok": False, "message": f"Ollama 服务无法连接: {self.base_url}"}
        # 仅检查连通性，模型级检查由 StoryLLMClient 按需校验
        return {"ok": True, "message": "Ollama 健康检查通过。"}

    def assert_ready(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                return  # already in async context; trust upstream node
        except RuntimeError:
            pass
        res = asyncio.run(self.health_check_async())
        if not res["ok"]:
            raise RuntimeError(res["message"])

    async def chat_async(
        self,
        model: str,
        prompt: str,
        temperature: float,
        token_callback: Optional[Callable[[dict], None]] = None,
        event_meta: Optional[dict] = None,
        response_format: Optional[str] = None,
    ) -> str:
        llm = ChatOllama(
            model=model,
            base_url=self.base_url,
            temperature=self.default_temperature if temperature is None else temperature,
            format=response_format,
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
