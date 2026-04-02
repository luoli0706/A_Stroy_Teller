import json
import os
from urllib.request import Request, urlopen


DEFAULT_EMBED_MODEL = "nomic-embed-text-v2-moe"


class OllamaEmbeddingClient:
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL_EMBEDDING", DEFAULT_EMBED_MODEL)

    def _post_json(self, path: str, payload: dict, timeout: float = 30.0) -> dict:
        url = self.base_url + path
        body = json.dumps(payload).encode("utf-8")
        req = Request(url=url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        cleaned = [text.strip() for text in texts if text and text.strip()]
        if not cleaned:
            return []

        try:
            payload = self._post_json(
                "/api/embed",
                {"model": self.model, "input": cleaned},
            )
            embeddings = payload.get("embeddings", [])
            if embeddings and isinstance(embeddings, list):
                return [[float(val) for val in item] for item in embeddings]
        except Exception:
            pass

        # Backward compatibility for older Ollama endpoints.
        output: list[list[float]] = []
        for text in cleaned:
            payload = self._post_json(
                "/api/embeddings",
                {"model": self.model, "prompt": text},
            )
            embedding = payload.get("embedding", [])
            if not embedding:
                raise RuntimeError("Ollama embedding response missing 'embedding' field.")
            output.append([float(val) for val in embedding])

        return output
