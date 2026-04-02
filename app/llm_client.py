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
        except Exception:
            pass

    async def _chat_async(
        self,
        model: str,
        prompt: str,
        temperature: float | None = None,
        token_callback: Callable[[dict], None] | None = None,
        event_meta: dict | None = None,
        response_format: str | None = None,
    ) -> str:
        """核心异步聊天逻辑，支持流式 token 回调与 JSON 格式。"""
        llm = ChatOllama(
            model=model,
            base_url=self.base_url,
            temperature=self.temperature if temperature is None else temperature,
            format=response_format
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
            f"Topic: {topic}\nStyle: {style}\nActors (Real Names): {', '.join(role_ids)}\n\n"
            f"Story framework & Role Slots:\n{framework}\n\n"
            "INSTRUCTION: Map each Actor to a Slot. If more Actors than Slots, create new roles. "
            "Use Actors' real names in the outline.\n\n"
            "Output format:\n- Role Mapping: [Actor Name] -> [Slot Name]\n- Act 1\n- Act 2\n- Act 3\n- Shared facts"
        )
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.5,
            token_callback=token_callback,
            event_meta={"node": "plan_global_story"}
        )

    async def adapt_role_to_framework_async(
        self,
        role_id: str,
        generic_profile: str,
        framework: str,
        outline: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        """[v0.2.2] 让演员根据通用设定和故事大纲，生成在本故事中的特定身份。"""
        prompt = (
            "You are an actor preparing for a role in a story.\n"
            f"Your Real Identity (Generic Profile):\n{generic_profile}\n\n"
            f"Story Framework:\n{framework}\n\n"
            f"Global Outline:\n{outline}\n\n"
            "TASK: Based on your personality and the story needs, generate your 'Temporary Story Identity'.\n"
            "Decide your specific job/role in this story and how your traits manifest here.\n"
            "Output Format (JSON):\n"
            "{\n"
            "  'story_name': '...', \n"
            "  'story_personality_manifestation': '...', \n"
            "  'story_specific_goal': '...', \n"
            "  'story_key_items': ['...']\n"
            "}"
        )
        return await self._chat_async(
            self.model_role, prompt, temperature=0.7,
            token_callback=token_callback,
            event_meta={"node": "adapt_roles_to_framework", "role_id": role_id},
            response_format="json"
        )

    async def generate_role_view_async(
        self,
        role_id: str,
        generic_profile: str,
        story_identity: str,
        memory: str,
        rag_context: str,
        outline: str,
        style: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "You are writing one role-specific narrative in first person. "
            f"Real Identity:\n{generic_profile}\n"
            f"Story-Specific Identity:\n{story_identity}\n\n"
            f"Style: {style}\nGlobal outline:\n{outline}\n\n"
            f"Past Memories:\n{memory}\n"
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
            "Evaluate story consistency. Return ONLY a JSON object with fields: "
            "'status' (PASS/FAIL), 'score' (0-10), 'conflicts' (list of strings), 'suggestions' (list).\n\n"
            f"Roles: {', '.join(role_ids)}\nOutline:\n{outline}\n\nStory:\n{integrated_story}"
        )
        return await self._chat_async(
            self.model_quality, prompt, temperature=0.1,
            token_callback=token_callback,
            event_meta={"node": "quality_check"},
            response_format="json"
        )

_client_instance = None

def get_story_client() -> OllamaStoryClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = OllamaStoryClient()
    return _client_instance
