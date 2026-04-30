from app.config import LLM_PROVIDER, resolve_embedding_provider
from app.llm.base import BaseLLMProvider, BaseEmbeddingProvider


def create_llm_provider(provider_name: str = "") -> BaseLLMProvider:
    """根据 Provider 名称创建 LLM Provider 实例。"""
    name = (provider_name or LLM_PROVIDER).lower().strip()

    if name == "openai":
        from app.llm.openai import OpenAIProvider
        return OpenAIProvider()

    if name == "anthropic":
        from app.llm.anthropic import AnthropicProvider
        return AnthropicProvider()

    if name == "ollama":
        from app.llm.ollama import OllamaProvider
        return OllamaProvider()

    raise ValueError(f"不支持的 LLM_PROVIDER: {name!r}，可选值: ollama, openai, anthropic")


def create_embedding_provider(provider_name: str = "") -> BaseEmbeddingProvider:
    """根据 Provider 名称创建 Embedding Provider 实例。

    若未指定，使用 resolve_embedding_provider() 自动推断。
    """
    name = (provider_name or resolve_embedding_provider()).lower().strip()

    if name == "openai":
        from app.llm.openai_embed import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider()

    # 默认 ollama（含 anthropic 回退场景）
    from app.llm.ollama_embed import OllamaEmbeddingProvider
    return OllamaEmbeddingProvider()
