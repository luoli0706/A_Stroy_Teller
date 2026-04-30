import httpx

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL_EMBEDDING
from app.llm.base import BaseEmbeddingProvider


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama Embedding Provider。"""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL_EMBEDDING,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        cleaned = [text.strip() for text in texts if text and text.strip()]
        if not cleaned:
            return []

        url = f"{self.base_url}/api/embed"
        payload = {"model": self.model, "input": cleaned}

        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                return [[float(val) for val in item] for item in embeddings]
        except Exception as e:
            print(f"Embedding error: {e}")
            return []
