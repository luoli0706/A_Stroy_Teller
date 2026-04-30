"""配置加载测试（pytest 风格）。"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import (
    init_config,
    get_effective_model_config,
    resolve_embedding_provider,
    LLM_PROVIDER,
    BASE_DIR,
    DATA_DIR,
    SQLITE_DB_PATH,
)


class TestInitConfig:
    def test_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.config.DATA_DIR", tmp_path / ".data")
        monkeypatch.setattr("app.config.LOG_DIR", tmp_path / "logs")
        monkeypatch.setattr("app.config.OPT_STORIES_DIR", tmp_path / "opt" / "stories")
        # 多次调用不应出错
        init_config()
        init_config()
        init_config()

    def test_dirs_created(self, tmp_path, monkeypatch):
        data = tmp_path / ".data"
        logs = tmp_path / "logs"
        opt = tmp_path / "opt" / "stories"
        monkeypatch.setattr("app.config.DATA_DIR", data)
        monkeypatch.setattr("app.config.LOG_DIR", logs)
        monkeypatch.setattr("app.config.OPT_STORIES_DIR", opt)
        init_config()
        assert data.exists()
        assert logs.exists()
        assert opt.exists()


class TestPathConfig:
    def test_base_dir_is_absolute(self):
        assert BASE_DIR.is_absolute()

    def test_sqlite_db_in_data(self):
        assert SQLITE_DB_PATH.parent.name == ".data"

    def test_data_dir_relative(self):
        assert DATA_DIR == BASE_DIR / ".data"


class TestEffectiveModelConfig:
    def test_default_ollama(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        cfg = get_effective_model_config()
        assert cfg["provider"] == "ollama"
        assert "planner" in cfg
        assert "embedding" in cfg

    def test_openai(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        cfg = get_effective_model_config()
        assert cfg["provider"] == "openai"
        assert cfg["planner"] == "gpt-4o"

    def test_anthropic(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        cfg = get_effective_model_config()
        assert cfg["provider"] == "anthropic"
        assert cfg["embedding"] == ""  # Anthropic 无 embedding

    def test_quality_follows_integrator(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("OLLAMA_MODEL_QUALITY", "")
        cfg = get_effective_model_config()
        assert cfg["quality"] == cfg["integrator"]


class TestResolveEmbeddingProvider:
    def test_explicit(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
        assert resolve_embedding_provider() == "openai"

    def test_anthropic_fallback(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "")
        assert resolve_embedding_provider() == "ollama"

    def test_openai_native(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "")
        assert resolve_embedding_provider() == "openai"

    def test_ollama_default(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "")
        assert resolve_embedding_provider() == "ollama"
