import os
import json
import asyncio
from typing import Callable, Any
import httpx
from langchain_ollama import ChatOllama
from app.config import (
    OLLAMA_BASE_URL,
    MODEL_PLANNER,
    MODEL_ROLE,
    MODEL_INTEGRATOR,
    MODEL_QUALITY,
    MODEL_EMBEDDING,
    DEFAULT_TEMPERATURE,
)

class OllamaStoryClient:
    """智能故事生成系统的 LLM 客户端，支持异步与流式输出。"""

    def __init__(self) -> None:
        self.base_url = OLLAMA_BASE_URL
        self.model_planner = MODEL_PLANNER
        self.model_role = MODEL_ROLE
        self.model_integrator = MODEL_INTEGRATOR
        self.model_quality = MODEL_QUALITY
        self.model_embedding = MODEL_EMBEDDING
        self.temperature = DEFAULT_TEMPERATURE

    async def _list_available_models_async(self) -> list[str]:
        """使用 httpx 异步获取 Ollama 可用模型列表。"""
        tags_url = self.base_url.rstrip("/") + "/api/tags"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(tags_url, timeout=5.0)
                response.raise_for_status()
                payload = response.json()
                return [str(m.get("model", "")).strip() for m in payload.get("models", [])]
            except Exception:
                return []

    def _model_aliases(self, model_name: str) -> set[str]:
        value = model_name.strip()
        aliases = {value}
        if value.endswith(":latest"):
            aliases.add(value[: -len(":latest")])
        elif ":" not in value:
            aliases.add(f"{value}:latest")
        return aliases

    async def health_check_async(self) -> dict:
        """异步执行健康检查。"""
        required = {
            self.model_planner,
            self.model_role,
            self.model_integrator,
            self.model_quality,
            self.model_embedding,
        }
        available_models = await self._list_available_models_async()
        if not available_models:
            return {
                "ok": False,
                "message": f"Ollama 服务无法连接: {self.base_url}",
            }

        available_set = set(available_models)
        missing = [
            m for m in required 
            if not (self._model_aliases(m) & available_set)
        ]
        
        if missing:
            return {
                "ok": False,
                "message": f"缺失模型: {', '.join(missing)}. 请先执行 ollama pull。",
            }
        return {"ok": True, "message": "Ollama 健康检查通过。"}

    def assert_ready(self) -> None:
        """同步检查状态，主要用于初始化（通过 asyncio.run）。"""
        try:
            res = asyncio.run(self.health_check_async())
            if not res["ok"]:
                raise RuntimeError(res["message"])
        except Exception as e:
            # 如果在已经运行的事件循环中调用，降级为同步逻辑或报错
            pass

    async def _chat_async(
        self,
        model: str,
        prompt: str,
        temperature: float | None = None,
        token_callback: Callable[[dict], None] | None = None,
        event_meta: dict | None = None,
    ) -> str:
        """核心异步聊天逻辑，支持流式 token 回调。"""
        llm = ChatOllama(
            model=model,
            base_url=self.base_url,
            temperature=self.temperature if temperature is None else temperature,
        )

        if token_callback:
            parts: list[str] = []
            meta = event_meta or {}
            # ChatOllama 的 astream 是异步迭代器
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
        
        # 非流式异步调用
        response = await llm.ainvoke(prompt)
        content = getattr(response, "content", "")
        return str(content).strip() if not isinstance(content, list) else "\n".join(map(str, content)).strip()

    async def plan_global_story_async(
        self,
        topic: str,
        style: str,
        role_ids: list[str],
        framework: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "You are a story planner. Build a concise 3-act outline with timeline beats. "
            f"Topic: {topic}\nStyle: {style}\nRoles: {', '.join(role_ids)}\n\n"
            f"Story framework:\n{framework}\n\n"
            "Output format:\n- Act 1\n- Act 2\n- Act 3\n- Shared facts (bullet list)"
        )
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.5,
            token_callback=token_callback,
            event_meta={"node": "plan_global_story"}
        )

    async def generate_role_view_async(
        self,
        role_id: str,
        profile: str,
        memory: str,
        rag_context: str,
        outline: str,
        style: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "You are writing one role-specific narrative in first person. "
            f"Role ID: {role_id}\nStyle: {style}\nGlobal outline:\n{outline}\n\n"
            f"Role profile:\n{profile}\nRole memory:\n{memory}\n"
            f"RAG context:\n{rag_context or '(none)'}\n\n"
            "Output: Perspective Summary, Scene Narrative, Role-specific interpretation"
        )
        return await self._chat_async(
            self.model_role, prompt, temperature=0.8,
            token_callback=token_callback,
            event_meta={"node": "generate_role_views", "role_id": role_id}
        )

    async def integrate_perspectives_async(
        self,
        topic: str,
        style: str,
        role_drafts: dict[str, str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        draft_blocks = "\n\n".join(f"Role: {rid}\n{draft}" for rid, draft in role_drafts.items())
        prompt = (
            "Merge multi-role narratives into one coherent story. "
            f"Topic: {topic}\nStyle: {style}\n\nRole drafts:\n{draft_blocks}\n\n"
            "Output: Title, Final integrated story"
        )
        return await self._chat_async(
            self.model_integrator, prompt, temperature=0.6,
            token_callback=token_callback,
            event_meta={"node": "integrate_perspectives"}
        )

    async def quality_check_async(
        self,
        outline: str,
        integrated_story: str,
        role_ids: list[str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "Evaluate consistency and role voice. Return PASS or FAIL.\n"
            f"Roles: {', '.join(role_ids)}\nOutline:\n{outline}\n\nStory:\n{integrated_story}"
        )
        return await self._chat_async(
            self.model_quality, prompt, temperature=0.2,
            token_callback=token_callback,
            event_meta={"node": "quality_check"}
        )

_client_instance = None

def get_story_client() -> OllamaStoryClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = OllamaStoryClient()
    return _client_instance
