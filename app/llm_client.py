import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_ollama import ChatOllama


DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "Qwen3.5:9b"


class OllamaStoryClient:
    def __init__(self) -> None:
        load_dotenv()
        self.base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        self.model_planner = os.getenv("OLLAMA_MODEL_PLANNER", DEFAULT_MODEL)
        self.model_role = os.getenv("OLLAMA_MODEL_ROLE", DEFAULT_MODEL)
        self.model_integrator = os.getenv("OLLAMA_MODEL_INTEGRATOR", DEFAULT_MODEL)
        self.model_quality = os.getenv("OLLAMA_MODEL_QUALITY", self.model_integrator)
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

    def _chat(self, model: str, prompt: str, temperature: float | None = None) -> str:
        llm = ChatOllama(
            model=model,
            base_url=self.base_url,
            temperature=self.temperature if temperature is None else temperature,
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", "")
        if isinstance(content, list):
            return "\n".join(str(part) for part in content).strip()
        return str(content).strip()

    def plan_global_story(self, topic: str, style: str, role_ids: list[str]) -> str:
        prompt = (
            "You are a story planner. Build a concise 3-act outline with timeline beats. "
            "Keep it coherent for all roles.\n\n"
            f"Topic: {topic}\n"
            f"Style: {style}\n"
            f"Roles: {', '.join(role_ids)}\n\n"
            "Output format:\n"
            "- Act 1\n"
            "- Act 2\n"
            "- Act 3\n"
            "- Shared facts (bullet list)"
        )
        return self._chat(self.model_planner, prompt, temperature=0.5)

    def generate_role_view(
        self,
        role_id: str,
        profile: str,
        memory: str,
        outline: str,
        style: str,
    ) -> str:
        prompt = (
            "You are writing one role-specific narrative in first person. "
            "Preserve shared facts from the outline, but express role bias and voice.\n\n"
            f"Role ID: {role_id}\n"
            f"Style target: {style}\n"
            f"Global outline:\n{outline}\n\n"
            f"Role profile:\n{profile}\n\n"
            f"Role memory:\n{memory}\n\n"
            "Output:\n"
            "1) Perspective Summary\n"
            "2) Scene Narrative (short story section)\n"
            "3) Role-specific interpretation"
        )
        return self._chat(self.model_role, prompt, temperature=0.8)

    def integrate_perspectives(self, topic: str, style: str, role_drafts: dict[str, str]) -> str:
        draft_blocks = "\n\n".join(
            f"Role: {role_id}\n{draft}" for role_id, draft in role_drafts.items()
        )
        prompt = (
            "You are a chief editor. Merge multi-role narratives into one coherent story. "
            "Keep each role distinct while maintaining timeline consistency.\n\n"
            f"Topic: {topic}\n"
            f"Style: {style}\n\n"
            f"Role drafts:\n{draft_blocks}\n\n"
            "Output:\n"
            "- Title\n"
            "- Final integrated story"
        )
        return self._chat(self.model_integrator, prompt, temperature=0.6)

    def quality_check(self, outline: str, integrated_story: str, role_ids: list[str]) -> str:
        prompt = (
            "You are a strict story QA reviewer.\n"
            "Evaluate consistency, role voice separation, and timeline coherence.\n"
            "Return PASS or FAIL, then concise findings and one revision suggestion.\n\n"
            f"Roles: {', '.join(role_ids)}\n"
            f"Outline:\n{outline}\n\n"
            f"Integrated story:\n{integrated_story}"
        )
        return self._chat(self.model_quality, prompt, temperature=0.2)


@lru_cache(maxsize=1)
def get_story_client() -> OllamaStoryClient:
    return OllamaStoryClient()
