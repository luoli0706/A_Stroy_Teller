from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类。"""

    @abstractmethod
    async def chat_async(
        self,
        model: str,
        prompt: str,
        temperature: float,
        token_callback: Optional[Callable[[dict], None]] = None,
        event_meta: Optional[dict] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """异步 LLM 对话，支持流式 token 回调。"""
        ...

    @abstractmethod
    async def health_check_async(self) -> dict:
        """异步健康检查，返回 {"ok": bool, "message": str}。"""
        ...

    def assert_ready(self) -> None:
        """同步断言 Provider 已就绪；若不可用则抛出异常。"""
        ...


class BaseEmbeddingProvider(ABC):
    """Embedding Provider 抽象基类。"""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量获取文本嵌入向量。"""
        ...
