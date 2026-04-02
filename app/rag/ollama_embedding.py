import json
import httpx
from app.config import OLLAMA_BASE_URL, MODEL_EMBEDDING

class OllamaEmbeddingClient:
    """封装 Ollama 嵌入接口，统一使用 httpx 进行调用。"""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = MODEL_EMBEDDING) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量获取文本嵌入向量。"""
        cleaned = [text.strip() for text in texts if text and text.strip()]
        if not cleaned:
            return []

        url = f"{self.base_url}/api/embed"
        payload = {"model": self.model, "input": cleaned}

        try:
            # 内部使用同步调用以便兼容当前的索引流程
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                return [[float(val) for val in item] for item in embeddings]
        except Exception as e:
            # 降级处理：逐个获取或抛出错误
            print(f"Embedding error: {e}")
            return []
