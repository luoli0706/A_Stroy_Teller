import os
from dataclasses import dataclass
from functools import lru_cache
import json
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv
from langchain_ollama import ChatOllama


DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.5:9b"
DEFAULT_EMBED_MODEL = "nomic-embed-text-v2-moe"


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    message: str


class OllamaStoryClient:
    def __init__(self) -> None:
        load_dotenv()
        self.base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        self.model_planner = os.getenv("OLLAMA_MODEL_PLANNER", DEFAULT_MODEL)
        self.model_role = os.getenv("OLLAMA_MODEL_ROLE", DEFAULT_MODEL)
        self.model_integrator = os.getenv("OLLAMA_MODEL_INTEGRATOR", DEFAULT_MODEL)
        self.model_quality = os.getenv("OLLAMA_MODEL_QUALITY", self.model_integrator)
        self.model_embedding = os.getenv("OLLAMA_MODEL_EMBEDDING", DEFAULT_EMBED_MODEL)
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

    def _list_available_models(self) -> list[str]:
        tags_url = self.base_url.rstrip("/") + "/api/tags"
        with urlopen(tags_url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        names: list[str] = []
        for model in payload.get("models", []):
            model_name = str(model.get("model", "")).strip()
            if model_name:
                names.append(model_name)
        return names

    def _model_aliases(self, model_name: str) -> set[str]:
        value = model_name.strip()
        aliases = {value}
        if value.endswith(":latest"):
            aliases.add(value[: -len(":latest")])
        elif ":" not in value:
            aliases.add(f"{value}:latest")
        return aliases

    def health_check(self) -> HealthCheckResult:
        required = {
            self.model_planner,
            self.model_role,
            self.model_integrator,
            self.model_quality,
            self.model_embedding,
        }
        try:
            available_models = self._list_available_models()
        except URLError:
            return HealthCheckResult(
                ok=False,
                message=(
                    "Ollama service is unreachable. "
                    f"Check OLLAMA_BASE_URL={self.base_url} and ensure Ollama is running."
                ),
            )
        except Exception as exc:
            return HealthCheckResult(ok=False, message=f"Failed to query Ollama tags: {exc}")

        available_set = set(available_models)
        missing = sorted(
            model
            for model in required
            if not (self._model_aliases(model) & available_set)
        )
        if missing:
            return HealthCheckResult(
                ok=False,
                message=(
                    "Missing Ollama models: "
                    + ", ".join(missing)
                    + ". Pull them first, for example: ollama pull "
                    + missing[0]
                ),
            )

        return HealthCheckResult(ok=True, message="Ollama health check passed.")

    def assert_ready(self) -> None:
        result = self.health_check()
        if not result.ok:
            raise RuntimeError(result.message)

    def _chat(
        self,
        model: str,
        prompt: str,
        temperature: float | None = None,
        token_callback: Callable[[dict], None] | None = None,
        event_meta: dict | None = None,
    ) -> str:
        llm = ChatOllama(
            model=model,
            base_url=self.base_url,
            temperature=self.temperature if temperature is None else temperature,
        )

        if token_callback is not None:
            parts: list[str] = []
            meta = event_meta or {}
            for chunk in llm.stream(prompt):
                content = getattr(chunk, "content", "")
                text = ""
                if isinstance(content, list):
                    text = "".join(str(part) for part in content)
                else:
                    text = str(content)

                if text:
                    parts.append(text)
                    token_callback(
                        {
                            "event": "token",
                            "node": meta.get("node", ""),
                            "model": model,
                            "role_id": meta.get("role_id", ""),
                            "text": text,
                        }
                    )
            return "".join(parts).strip()

        response = llm.invoke(prompt)
        content = getattr(response, "content", "")
        if isinstance(content, list):
            return "\n".join(str(part) for part in content).strip()
        return str(content).strip()

    def plan_global_story(
        self,
        topic: str,
        style: str,
        role_ids: list[str],
        framework: str,
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "You are a story planner. Build a concise 3-act outline with timeline beats. "
            "Keep it coherent for all roles.\n\n"
            f"Topic: {topic}\n"
            f"Style: {style}\n"
            f"Roles: {', '.join(role_ids)}\n\n"
            f"Story framework:\n{framework}\n\n"
            "Output format:\n"
            "- Act 1\n"
            "- Act 2\n"
            "- Act 3\n"
            "- Shared facts (bullet list)"
        )
        return self._chat(
            self.model_planner,
            prompt,
            temperature=0.5,
            token_callback=token_callback,
            event_meta={"node": "plan_global_story"},
        )

    def generate_role_view(
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
            "Preserve shared facts from the outline, but express role bias and voice.\n\n"
            f"Role ID: {role_id}\n"
            f"Style target: {style}\n"
            f"Global outline:\n{outline}\n\n"
            f"Role profile:\n{profile}\n\n"
            f"Role memory:\n{memory}\n\n"
            f"RAG memory context from same story framework:\n{rag_context or '(none)'}\n\n"
            "Output:\n"
            "1) Perspective Summary\n"
            "2) Scene Narrative (short story section)\n"
            "3) Role-specific interpretation"
        )
        return self._chat(
            self.model_role,
            prompt,
            temperature=0.8,
            token_callback=token_callback,
            event_meta={"node": "generate_role_views", "role_id": role_id},
        )

    def integrate_perspectives(
        self,
        topic: str,
        style: str,
        role_drafts: dict[str, str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
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
        return self._chat(
            self.model_integrator,
            prompt,
            temperature=0.6,
            token_callback=token_callback,
            event_meta={"node": "integrate_perspectives"},
        )

    def quality_check(
        self,
        outline: str,
        integrated_story: str,
        role_ids: list[str],
        token_callback: Callable[[dict], None] | None = None,
    ) -> str:
        prompt = (
            "You are a strict story QA reviewer.\n"
            "Evaluate consistency, role voice separation, and timeline coherence.\n"
            "Return PASS or FAIL, then concise findings and one revision suggestion.\n\n"
            f"Roles: {', '.join(role_ids)}\n"
            f"Outline:\n{outline}\n\n"
            f"Integrated story:\n{integrated_story}"
        )
        return self._chat(
            self.model_quality,
            prompt,
            temperature=0.2,
            token_callback=token_callback,
            event_meta={"node": "quality_check"},
        )


@lru_cache(maxsize=1)
def get_story_client() -> OllamaStoryClient:
    return OllamaStoryClient()
