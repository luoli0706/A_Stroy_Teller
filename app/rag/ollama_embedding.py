"""向下兼容模块 —— 重导出至新位置 app.llm.ollama_embed。

原有 `OllamaEmbeddingClient` 现在位于:
    from app.llm.ollama_embed import OllamaEmbeddingProvider

推荐使用工厂函数:
    from app.llm.factory import create_embedding_provider
"""

from app.llm.ollama_embed import OllamaEmbeddingProvider as OllamaEmbeddingClient  # noqa: F401
