"""图节点单元测试（使用 mock provider）。"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.state import StoryState, RoleStoryIdentity, QualityReport
from app.graph import (
    Result,
    robust_task,
    collect_requirements,
    load_story_framework_node,
    load_roles,
    map_roles_to_slots,
    adapt_roles_to_framework,
    generate_role_views,
    quality_check,
    route_after_quality,
    finalize_output,
    distill_memories,
)


class TestResult:
    def test_ok(self):
        r = Result(value="hello")
        assert r.ok is True
        assert r.value == "hello"
        assert r.error is None

    def test_error(self):
        r = Result(error="something went wrong")
        assert r.ok is False
        assert r.value is None
        assert r.error == "something went wrong"


class TestRobustTask:
    @pytest.mark.asyncio
    async def test_success(self, sample_state):
        async def ok_coro():
            return "success"
        result = await robust_task(ok_coro(), "RoleA", "test_node", sample_state)
        assert result.ok
        assert result.value == "success"

    @pytest.mark.asyncio
    async def test_failure(self, sample_state):
        async def fail_coro():
            raise RuntimeError("simulated failure")
        result = await robust_task(fail_coro(), "RoleB", "test_node", sample_state)
        assert not result.ok
        assert "simulated failure" in (result.error or "")


class TestCollectRequirements:
    @pytest.mark.asyncio
    async def test_defaults(self, sample_state, monkeypatch, tmp_path):
        monkeypatch.setattr("app.graph.SQLITE_DB_PATH", tmp_path / "test.db")
        monkeypatch.setattr("app.graph.ROLE_DIR", tmp_path / "role")
        # Mock dependencies
        with patch("app.graph.init_db") as mock_init_db, \
             patch("app.graph.init_metadata_db") as mock_init_meta, \
             patch("app.graph.create_story_client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client.assert_ready = MagicMock()
            mock_client_factory.return_value = mock_client

            result = await collect_requirements(sample_state)
            assert "roles" in result
            assert "run_id" in result
            assert result["run_id"] is not None


class TestLoadStoryFramework:
    @pytest.mark.asyncio
    async def test_missing_fallback(self, sample_state, tmp_path):
        stories_dir = tmp_path / "stories"
        result = await load_story_framework_node(sample_state)
        assert "story_framework" in result
        assert len(result["story_framework"]) > 0


class TestLoadRoles:
    @pytest.mark.asyncio
    async def test_empty_role_dir(self, sample_state, tmp_path, monkeypatch):
        role_dir = tmp_path / "role"
        role_dir.mkdir()
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        monkeypatch.setattr("app.graph.ROLE_DIR", str(role_dir))
        monkeypatch.setattr("app.graph.MEMORY_DIR", str(memory_dir))
        monkeypatch.setattr("app.graph.SQLITE_DB_PATH", str(tmp_path / "test.db"))
        with patch("app.graph.upsert_role_asset"):
            result = await load_roles(sample_state)
            assert "role_assets" in result


class TestQualityRouting:
    def test_pass_routes_to_finalize(self):
        state = StoryState(
            quality_report=QualityReport(status="PASS"),
            retry_count=0,
        )
        assert route_after_quality(state) == "finalize_output"

    def test_fail_under_max_routes_to_retry(self):
        state = StoryState(
            quality_report=QualityReport(status="FAIL"),
            retry_count=0,
            max_retry=2,
        )
        assert route_after_quality(state) == "generate_role_views"

    def test_fail_over_max_routes_to_finalize(self):
        state = StoryState(
            quality_report=QualityReport(status="FAIL"),
            retry_count=3,
            max_retry=2,
        )
        assert route_after_quality(state) == "finalize_output"


class TestAdaptRolesToFramework:
    @pytest.mark.asyncio
    async def test_handles_mixed_results(self, sample_state, monkeypatch):
        """验证 Result 类型能正确处理混合的成功/失败结果。"""
        sample_state.role_assets = {
            "RoleA": {"profile": "profile A"},
            "RoleB": {"profile": "profile B"},
        }
        sample_state.roles = ["RoleA", "RoleB"]

        mock_client = MagicMock()
        mock_client.adapt_role_to_framework_async = AsyncMock(side_effect=[
            '{"story_name":"A","story_personality_manifestation":"brave","story_specific_goal":"win","story_key_items":[]}',
            Exception("Provider error"),
        ])
        mock_client.generate_relationships_async = AsyncMock(return_value="relations")

        with patch("app.graph.create_story_client", return_value=mock_client):
            result = await adapt_roles_to_framework(sample_state)
            assert "role_story_identities" in result
            identities = result["role_story_identities"]
            # RoleA should succeed
            assert identities["RoleA"].story_specific_goal == "win"
            # RoleB should get fallback identity
            assert identities["RoleB"].story_specific_goal == "Explore"


class TestGenerateRoleViews:
    @pytest.mark.asyncio
    async def test_error_role_gets_placeholder(self, sample_state):
        sample_state.role_assets = {"RoleA": {"profile": "p", "memory": ""}}
        sample_state.roles = ["RoleA"]
        sample_state.role_story_identities = {
            "RoleA": RoleStoryIdentity(story_name="A", story_personality_manifestation="p", story_specific_goal="g")
        }
        sample_state.rag_role_contexts = {"RoleA": ""}

        mock_client = MagicMock()
        mock_client.generate_role_view_async = AsyncMock(side_effect=RuntimeError("fail"))

        with patch("app.graph.create_story_client", return_value=mock_client):
            result = await generate_role_views(sample_state)
            views = result["role_view_drafts"]
            assert "[RoleA perspective unavailable" in views["RoleA"]


class TestFinalizeOutput:
    @pytest.mark.asyncio
    async def test_writes_output(self, sample_state, tmp_path, monkeypatch):
        sample_state.integrated_draft = "Final story content"
        sample_state.run_id = 999
        sample_state.role_view_drafts = {"RoleA": "Role A view"}

        opt_dir = tmp_path / "opt"
        monkeypatch.setattr("app.graph.OPT_STORIES_DIR", opt_dir)
        monkeypatch.setattr("app.graph.SQLITE_DB_PATH", str(tmp_path / "test.db"))
        with patch("app.graph.update_story_run"), \
             patch("app.graph.persist_generated_role_slice", return_value=tmp_path / "slice.md"):
            result = await finalize_output(sample_state)
            assert result["final_story"] == "Final story content"
            assert result["run_id"] == 999
