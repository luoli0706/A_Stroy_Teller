import os
import json
import asyncio
from typing import Callable, Any, List, Dict
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
        required = {self.model_planner, self.model_role, self.model_integrator, self.model_quality, self.model_embedding}
        available_models = await self._list_available_models_async()
        if not available_models:
            return {"ok": False, "message": f"Ollama 服务无法连接: {self.base_url}"}
        available_set = set(available_models)
        missing = [m for m in required if not (self._model_aliases(m) & available_set)]
        if missing:
            return {"ok": False, "message": f"缺失模型: {', '.join(missing)}. 请先执行 ollama pull。"}
        return {"ok": True, "message": "Ollama 健康检查通过。"}

    def assert_ready(self) -> None:
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

    async def map_roles_to_slots_async(self, roles: List[str], role_profiles: Dict[str, str], framework: str) -> str:
        """[v0.2.3] 独立的角色分配节点。"""
        profiles_summary = "\n".join([f"Actor [{rid}]: {profile[:200]}..." for rid, profile in role_profiles.items()])
        prompt = (
            "You are a casting director. Assign each Actor to a Role Slot from the framework.\n"
            f"Actors:\n{profiles_summary}\n\n"
            f"Story Framework:\n{framework}\n\n"
            "Return a JSON object where keys are Actor IDs and values are Slot Names.\n"
            "If an actor doesn't fit any slot, assign them as 'New Character: [Proposed Role Name]'."
        )
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.2,
            event_meta={"node": "role_mapping"},
            response_format="json"
        )

    async def plan_global_story_async(
        self,
        topic: str,
        style: str,
        role_mapping: Dict[str, str],
        framework: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        mapping_str = "\n".join([f"{actor} plays {slot}" for actor, slot in role_mapping.items()])
        prompt = (
            "You are a story planner. Build a concise 3-act outline with timeline beats. "
            f"Topic: {topic}\nStyle: {style}\n\n"
            f"Cast Assignment:\n{mapping_str}\n\n"
            f"Story framework:\n{framework}\n\n"
            "Output format:\n- Act 1\n- Act 2\n- Act 3\n- Shared facts"
        )
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.5,
            token_callback=token_callback,
            event_meta={"node": "plan_global_story"}
        )

    async def generate_relationships_async(self, role_ids: List[str], identities: Dict[str, str]) -> str:
        """[v0.2.3] 生成初始社交关系网。"""
        ids_summary = "\n".join([f"{rid}: {info}" for rid, info in identities.items()])
        prompt = (
            "Generate a social relationship matrix for these characters in the current story.\n"
            f"Cast:\n{ids_summary}\n\n"
            "Describe the initial attitude, conflict, or bond between each pair."
        )
        return await self._chat_async(self.model_planner, prompt, temperature=0.6)

    async def adapt_role_to_framework_async(
        self,
        role_id: str,
        generic_profile: str,
        framework: str,
        outline: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "You are an actor preparing for a role. CRITICAL: Your core personality must remain consistent.\n"
            f"Your Real Identity (Generic Profile):\n{generic_profile}\n\n"
            f"Story Framework:\n{framework}\n\n"
            f"Global Outline:\n{outline}\n\n"
            "TASK: Generate your 'Temporary Story Identity'. Ensure your traits manifest authentically in this new context.\n"
            "Output Format (JSON): {'story_name', 'story_personality_manifestation', 'story_specific_goal', 'story_key_items'}"
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
        relationships: str,
        memory: str,
        rag_context: str,
        outline: str,
        style: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "You are writing one role-specific narrative in first person. "
            f"REAL IDENTITY (DO NOT BREAK CHARACTER):\n{generic_profile}\n"
            f"STORY IDENTITY:\n{story_identity}\n"
            f"RELATIONSHIPS:\n{relationships}\n\n"
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
        role_drafts: Dict[str, str],
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
        role_ids: List[str],
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
