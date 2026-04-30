"""pytest 共享 fixtures。"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保项目根在 sys.path
_proj_root = Path(__file__).resolve().parents[1]
if str(_proj_root) not in sys.path:
    sys.path.insert(0, str(_proj_root))


@pytest.fixture
def temp_dir():
    """临时目录，测试结束后自动清理。"""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def mock_ollama_provider():
    """模拟 Ollama Provider。"""
    provider = MagicMock()
    provider.chat_async = AsyncMock(return_value="Mocked Ollama response")
    provider.health_check_async = AsyncMock(return_value={"ok": True, "message": "OK"})
    provider.assert_ready = MagicMock(return_value=None)
    return provider


@pytest.fixture
def mock_openai_provider():
    """模拟 OpenAI Provider。"""
    provider = MagicMock()
    provider.chat_async = AsyncMock(return_value='{"key": "value"}')
    provider.health_check_async = AsyncMock(return_value={"ok": True, "message": "OK"})
    provider.assert_ready = MagicMock(return_value=None)
    return provider


@pytest.fixture
def mock_anthropic_provider():
    """模拟 Anthropic Provider。"""
    provider = MagicMock()
    provider.chat_async = AsyncMock(return_value="Mocked Claude response")
    provider.health_check_async = AsyncMock(return_value={"ok": True, "message": "OK"})
    provider.assert_ready = MagicMock(return_value=None)
    return provider


@pytest.fixture
def sample_state():
    """最小可用的 StoryState 实例。"""
    from app.state import StoryState
    return StoryState(
        story_id="test_story",
        topic="a test topic",
        style="suspense",
        roles=["RoleA", "RoleB"],
        max_retry=1,
        rag_enabled=False,
        rag_top_k=2,
    )


@pytest.fixture(autouse=True)
def clean_config_cache():
    """每个测试前清除配置缓存状态。"""
    import app.config as cfg
    cfg._config_initialized = False
    yield
    cfg._config_initialized = False


@pytest.fixture
def temp_db(tmp_path):
    """临时 SQLite 数据库路径。"""
    db_path = tmp_path / "test.db"
    return str(db_path)


@pytest.fixture
def temp_metadata_db(tmp_path, monkeypatch):
    """临时 metadata.db 路径。"""
    db_path = tmp_path / "metadata.db"
    monkeypatch.setattr("app.metadata_store.METADATA_DB_PATH", db_path)
    from app.metadata_store import init_metadata_db
    init_metadata_db()
    return db_path


@pytest.fixture
def sample_markdown_text():
    """标准 Markdown 文本（含 front matter）。"""
    return (
        "---\n"
        "story_id: test_story\n"
        "role_id: TestRole\n"
        "chapter_timestamp: 20260401T120000Z\n"
        "run_id: 1\n"
        "---\n"
        "## Chapter 1\n"
        "This is chapter content.\n"
        "## Chapter 2\n"
        "More content here.\n"
    )
