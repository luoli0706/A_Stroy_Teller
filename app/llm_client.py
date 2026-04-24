import os
import json
import re
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

# [v0.3] 章节分隔标记，用于将既定事实切分为章节块。
# 使用独立的正则模式以避免将包含这些词的普通行（如角色名）误判为章节分隔符。
_CHAPTER_SPLIT_PATTERN = re.compile(
    r"^\s*(act\s+[1-9]|chapter\s+[1-9]|第[一二三四五六七八九十]+[幕章])\s*",
    re.IGNORECASE,
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
        """确保 Ollama 服务和所需模型已就绪。"""
        # 如果已有循环在运行，则跳过 asyncio.run 以免冲突
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # 这种情况下我们无法简单地进行异步健康检查并抛出异常，
                # 但在 LangGraph 节点内部，我们可以直接调用 health_check_async。
                return
        except RuntimeError:
            pass

        res = asyncio.run(self.health_check_async())
        if not res["ok"]:
            raise RuntimeError(res["message"])

    def health_check(self) -> Any:
        """同步健康检查封装。"""
        return asyncio.run(self.health_check_async())

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

    async def generate_established_facts_async(
        self,
        topic: str,
        style: str,
        global_outline: str,
        role_mapping: Dict[str, str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        """[v0.3] 从全局大纲中提炼既定事实时间线与世界观设定。

        产物供两个用途：
        1. 索引到 RAG 向量库，作为角色视角生成时的权威参照（替代跨角色记忆切片的相互引用）。
        2. 在整合阶段作为各章节的锚点，化解上下文窗口压力。
        """
        mapping_str = "\n".join([f"{actor} plays {slot}" for actor, slot in role_mapping.items()])
        prompt = (
            "You are a story bible writer. Based on the global outline, extract two structured sections:\n\n"
            "## ESTABLISHED FACTS (既定事实)\n"
            "List all key story events as objective facts in chronological order. "
            "Each fact should be a concise statement of WHAT happened, WHEN, WHERE, and WHO was involved. "
            "These are the authoritative ground-truth events that ALL characters must agree on.\n"
            "Format: [Timestamp/Chapter] Fact description\n\n"
            "## WORLD BIBLE (世界观设定)\n"
            "Describe the story world: setting, rules, atmosphere, and any special lore relevant to this story.\n\n"
            f"Topic: {topic}\nStyle: {style}\n\n"
            f"Cast:\n{mapping_str}\n\n"
            f"Global Outline:\n{global_outline}\n\n"
            "Output both sections clearly labeled."
        )
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.3,
            token_callback=token_callback,
            event_meta={"node": "generate_established_facts"}
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
        """[v0.3] 角色视角生成。

        RAG 上下文现在优先包含既定事实与世界观（而非其他角色的故事切片），
        确保各角色视角基于同一客观事件序列展开，消除因跨角色引用导致的逻辑矛盾。
        """
        prompt = (
            "You are writing one role-specific narrative in first person. "
            f"REAL IDENTITY (DO NOT BREAK CHARACTER):\n{generic_profile}\n"
            f"STORY IDENTITY:\n{story_identity}\n"
            f"RELATIONSHIPS:\n{relationships}\n\n"
            f"Style: {style}\nGlobal outline:\n{outline}\n\n"
            f"Past Memories:\n{memory}\n"
            "ESTABLISHED FACTS & WORLD BIBLE (authoritative ground truth — "
            "your narrative must respect these facts; add subjective detail and emotion, "
            "but do NOT contradict any listed fact):\n"
            f"{rag_context or '(none)'}\n\n"
            "Output: Perspective Summary, Scene Narrative, Role-specific interpretation"
        )
        return await self._chat_async(
            self.model_role, prompt, temperature=0.8,
            token_callback=token_callback,
            event_meta={"node": "generate_role_views", "role_id": role_id}
        )

    async def integrate_by_chapters_async(
        self,
        topic: str,
        style: str,
        established_facts: str,
        role_drafts: Dict[str, str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        """[v0.3] 按章节和既定事实整合多角色叙事，化解上下文窗口问题。

        策略：
        - 将既定事实切分为章节锚点（Act 1 / Act 2 / Act 3）。
        - 对每个章节，仅送入该章节相关的角色片段，输出对应章节故事段落。
        - 最后拼接各章节得到完整故事，避免一次性向 LLM 发送全部角色草稿。
        """
        # 从 established_facts 中识别章节分隔标记（仅匹配行首标记，防止误切）
        facts_lines = established_facts.splitlines()

        chapter_blocks: List[str] = []
        current: List[str] = []
        for line in facts_lines:
            if _CHAPTER_SPLIT_PATTERN.match(line) and current:
                chapter_blocks.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            chapter_blocks.append("\n".join(current))

        # 若无法切分章节，退回为单章处理
        if len(chapter_blocks) <= 1:
            chapter_blocks = [established_facts]

        chapter_stories: List[str] = []
        for idx, chapter_facts in enumerate(chapter_blocks, 1):
            draft_blocks = "\n\n".join(
                f"Role: {rid}\n{draft}" for rid, draft in role_drafts.items()
            )
            prompt = (
                f"You are merging multi-role narratives for Chapter {idx} of the story.\n"
                f"Topic: {topic}\nStyle: {style}\n\n"
                f"Chapter {idx} Established Facts (ground truth, must be respected):\n{chapter_facts}\n\n"
                f"Role drafts (use relevant sections only):\n{draft_blocks}\n\n"
                f"Output: A cohesive Chapter {idx} narrative that:\n"
                "- Aligns all character actions with the established facts\n"
                "- Preserves each character's voice and perspective\n"
                "- Resolves any conflicts by deferring to established facts\n"
                "- Keeps the designated style throughout"
            )
            chapter_text = await self._chat_async(
                self.model_integrator, prompt, temperature=0.6,
                token_callback=token_callback,
                event_meta={"node": "integrate_perspectives", "chapter": idx}
            )
            chapter_stories.append(f"## Chapter {idx}\n\n{chapter_text.strip()}")

        return "\n\n".join(chapter_stories)

    async def integrate_perspectives_async(
        self,
        topic: str,
        style: str,
        role_drafts: Dict[str, str],
        token_callback: Callable[[dict], None] | None = None,
        established_facts: str = "",
    ) -> str:
        """整合多角色叙事。若提供 established_facts 则使用章节化整合策略。"""
        if established_facts:
            return await self.integrate_by_chapters_async(
                topic, style, established_facts, role_drafts, token_callback
            )
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
