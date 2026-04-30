from langchain_openai import OpenAIEmbeddings

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_EMBEDDING
from app.llm.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI Embedding Provider。"""

    def __init__(
        self,
        api_key: str = OPENAI_API_KEY,
        base_url: str = OPENAI_BASE_URL,
        model: str = OPENAI_MODEL_EMBEDDING,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY 未设置，无法初始化 OpenAI Embedding Provider。")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        cleaned = [text.strip() for text in texts if text and text.strip()]
        if not cleaned:
            return []

        try:
            embeddings = OpenAIEmbeddings(
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
            )
            results = embeddings.embed_documents(cleaned)
            return [[float(val) for val in item] for item in results]
        except Exception as e:
            print(f"OpenAI Embedding error: {e}")
            return []
