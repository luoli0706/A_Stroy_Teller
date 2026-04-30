"""LLM Provider 实例化与接口测试。"""

import pytest
from unittest.mock import AsyncMock, patch

from app.llm.factory import create_llm_provider, create_embedding_provider
from app.llm.ollama import OllamaProvider
from app.llm.openai import OpenAIProvider
from app.llm.anthropic import AnthropicProvider
from app.llm.ollama_embed import OllamaEmbeddingProvider
from app.llm.openai_embed import OpenAIEmbeddingProvider


class TestCreateLLMProvider:
    def test_ollama_default(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        provider = create_llm_provider("ollama")
        assert isinstance(provider, OllamaProvider)

    def test_openai_requires_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = create_llm_provider("openai")
        assert isinstance(provider, OpenAIProvider)

    def test_openai_missing_key_raises(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            create_llm_provider("openai")

    def test_anthropic_requires_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        provider = create_llm_provider("anthropic")
        assert isinstance(provider, AnthropicProvider)

    def test_anthropic_missing_key_raises(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            create_llm_provider("anthropic")

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="不支持的 LLM_PROVIDER"):
            create_llm_provider("invalid_provider")

    def test_empty_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        provider = create_llm_provider("")
        assert isinstance(provider, OllamaProvider)


class TestCreateEmbeddingProvider:
    def test_default_ollama(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        provider = create_embedding_provider()
        assert isinstance(provider, OllamaEmbeddingProvider)

    def test_openai(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        provider = create_embedding_provider("openai")
        assert isinstance(provider, OpenAIEmbeddingProvider)

    def test_anthropic_fallback_to_ollama(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "")
        provider = create_embedding_provider()
        assert isinstance(provider, OllamaEmbeddingProvider)


class TestProviderHealthCheck:
    @pytest.mark.asyncio
    async def test_ollama_health_check_structure(self):
        provider = OllamaProvider()
        with patch.object(provider, '_list_models_async', return_value=["qwen3.5:9b"]):
            result = await provider.health_check_async()
            assert result["ok"] is True
            assert "message" in result

    @pytest.mark.asyncio
    async def test_ollama_health_check_unreachable(self):
        provider = OllamaProvider()
        with patch.object(provider, '_list_models_async', return_value=[]):
            result = await provider.health_check_async()
            assert result["ok"] is False


class TestStoryLLMClient:
    def test_create_with_provider(self, mock_ollama_provider):
        from app.llm_client import StoryLLMClient
        client = StoryLLMClient(mock_ollama_provider)
        assert client._llm is mock_ollama_provider

    def test_factory_creates_client(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        from app.llm_client import create_story_client
        client = create_story_client()
        from app.llm_client import StoryLLMClient
        assert isinstance(client, StoryLLMClient)

    def test_get_story_client_deprecated_alias(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        from app.llm_client import get_story_client
        client = get_story_client()
        from app.llm_client import StoryLLMClient
        assert isinstance(client, StoryLLMClient)


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, mock_ollama_provider):
        from app.llm_client import StoryLLMClient
        # 前两次失败，第三次成功
        mock_ollama_provider.chat_async = AsyncMock(side_effect=[
            ConnectionError("timeout"),
            ConnectionError("timeout"),
            "Success at last",
        ])
        client = StoryLLMClient(mock_ollama_provider)
        result = await client._chat_async("test-model", "test prompt", temperature=0.5)
        assert result == "Success at last"
        assert mock_ollama_provider.chat_async.call_count == 3
