import re
import json
import asyncio
from typing import Callable, Any, List, Dict

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import (
    LLM_PROVIDER,
    MAX_RETRY,
    LLM_REQUEST_RETRY,
    get_effective_model_config,
)
from app.llm.base import BaseLLMProvider
from app.llm.factory import create_llm_provider
from app.prompts import (
    casting_director_prompt,
    story_planner_prompt,
    relationship_matrix_prompt,
    role_adaptation_prompt,
    established_facts_prompt,
    role_view_prompt,
    integrate_simple_prompt,
    integrate_chapter_prompt,
    quality_check_prompt,
)

_CHAPTER_SPLIT_PATTERN = re.compile(
    r"^\s*(act\s+[1-9]|chapter\s+[1-9]|第[一二三四五六七八九十]+[幕章])\s*",
    re.IGNORECASE,
)


class StoryLLMClient:
    """智能故事生成系统的 LLM 客户端，支持多 Provider 注入。"""

    def __init__(self, llm_provider: BaseLLMProvider) -> None:
        self._llm = llm_provider
        cfg = get_effective_model_config()
        self.model_planner = cfg["planner"]
        self.model_role = cfg["role"]
        self.model_integrator = cfg["integrator"]
        self.model_quality = cfg["quality"]
        self.model_embedding = cfg["embedding"]
        # 从 config 模块读取温度（非 Ollama 专属）
        from app.config import DEFAULT_TEMPERATURE
        self.temperature = DEFAULT_TEMPERATURE

    # ── health check ──────────────────────────────────────────────────

    async def health_check_async(self) -> dict:
        return await self._llm.health_check_async()

    def health_check(self) -> Any:
        return asyncio.run(self.health_check_async())

    def assert_ready(self) -> None:
        self._llm.assert_ready()

    # ── internal chat with retry ──────────────────────────────────────

    async def _chat_async(
        self,
        model: str,
        prompt: str,
        temperature: float | None = None,
        token_callback: Callable[[dict], None] | None = None,
        event_meta: dict | None = None,
        response_format: str | None = None,
    ) -> str:
        temp = self.temperature if temperature is None else temperature
        return await self._chat_with_retry(
            model, prompt, float(temp), token_callback, event_meta, response_format
        )

    @retry(
        stop=stop_after_attempt(LLM_REQUEST_RETRY),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    async def _chat_with_retry(
        self,
        model: str,
        prompt: str,
        temperature: float,
        token_callback: Callable[[dict], None] | None,
        event_meta: dict | None,
        response_format: str | None,
    ) -> str:
        return await self._llm.chat_async(
            model, prompt, temperature,
            token_callback=token_callback,
            event_meta=event_meta,
            response_format=response_format,
        )

    # ── story pipeline methods ────────────────────────────────────────

    async def map_roles_to_slots_async(
        self, roles: List[str], role_profiles: Dict[str, str], framework: str
    ) -> str:
        profiles_summary = "\n".join(
            f"Actor [{rid}]: {profile[:200]}..." for rid, profile in role_profiles.items()
        )
        prompt = casting_director_prompt(profiles_summary, framework)
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.2,
            event_meta={"node": "role_mapping"},
            response_format="json",
        )

    async def plan_global_story_async(
        self,
        topic: str,
        style: str,
        role_mapping: Dict[str, str],
        framework: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        mapping_str = "\n".join(f"{actor} plays {slot}" for actor, slot in role_mapping.items())
        prompt = story_planner_prompt(topic, style, mapping_str, framework)
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.5,
            token_callback=token_callback,
            event_meta={"node": "plan_global_story"},
        )

    async def generate_relationships_async(
        self, role_ids: List[str], identities: Dict[str, str]
    ) -> str:
        ids_summary = "\n".join(f"{rid}: {info}" for rid, info in identities.items())
        prompt = relationship_matrix_prompt(ids_summary)
        return await self._chat_async(self.model_planner, prompt, temperature=0.6)

    async def adapt_role_to_framework_async(
        self,
        role_id: str,
        generic_profile: str,
        framework: str,
        outline: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = role_adaptation_prompt(generic_profile, framework, outline)
        return await self._chat_async(
            self.model_role, prompt, temperature=0.7,
            token_callback=token_callback,
            event_meta={"node": "adapt_roles_to_framework", "role_id": role_id},
            response_format="json",
        )

    async def generate_established_facts_async(
        self,
        topic: str,
        style: str,
        global_outline: str,
        role_mapping: Dict[str, str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        mapping_str = "\n".join(f"{actor} plays {slot}" for actor, slot in role_mapping.items())
        prompt = established_facts_prompt(topic, style, mapping_str, global_outline)
        return await self._chat_async(
            self.model_planner, prompt, temperature=0.3,
            token_callback=token_callback,
            event_meta={"node": "generate_established_facts"},
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
        prompt = role_view_prompt(
            generic_profile, story_identity, relationships,
            style, outline, memory, rag_context,
        )
        return await self._chat_async(
            self.model_role, prompt, temperature=0.8,
            token_callback=token_callback,
            event_meta={"node": "generate_role_views", "role_id": role_id},
        )

    async def integrate_by_chapters_async(
        self,
        topic: str,
        style: str,
        established_facts: str,
        role_drafts: Dict[str, str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
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

        if len(chapter_blocks) <= 1:
            chapter_blocks = [established_facts]

        chapter_stories: List[str] = []
        for idx, chapter_facts in enumerate(chapter_blocks, 1):
            draft_blocks = "\n\n".join(
                f"Role: {rid}\n{draft}" for rid, draft in role_drafts.items()
            )
            prompt = integrate_chapter_prompt(idx, topic, style, chapter_facts, draft_blocks)
            chapter_text = await self._chat_async(
                self.model_integrator, prompt, temperature=0.6,
                token_callback=token_callback,
                event_meta={"node": "integrate_perspectives", "chapter": idx},
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
        if established_facts:
            return await self.integrate_by_chapters_async(
                topic, style, established_facts, role_drafts, token_callback
            )
        draft_blocks = "\n\n".join(f"Role: {rid}\n{draft}" for rid, draft in role_drafts.items())
        prompt = integrate_simple_prompt(topic, style, draft_blocks)
        return await self._chat_async(
            self.model_integrator, prompt, temperature=0.6,
            token_callback=token_callback,
            event_meta={"node": "integrate_perspectives"},
        )

    async def quality_check_async(
        self,
        outline: str,
        integrated_story: str,
        role_ids: List[str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = quality_check_prompt(", ".join(role_ids), outline, integrated_story)
        return await self._chat_async(
            self.model_quality, prompt, temperature=0.1,
            token_callback=token_callback,
            event_meta={"node": "quality_check"},
            response_format="json",
        )


def create_story_client(provider_name: str = "") -> StoryLLMClient:
    """创建 StoryLLMClient 实例（工厂函数，替代旧有全局单例）。"""
    llm_provider = create_llm_provider(provider_name or LLM_PROVIDER)
    return StoryLLMClient(llm_provider)


# ── 向下兼容别名 ────────────────────────────────────────────────────

def get_story_client() -> StoryLLMClient:
    """[已弃用] 请使用 create_story_client()。

    保留此函数以兼容旧版调用代码。
    """
    return create_story_client()
