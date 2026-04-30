"""StoryState Pydantic 模型验证测试。"""

import pytest
from app.state import StoryState, RoleStoryIdentity, QualityReport


class TestRoleStoryIdentity:
    def test_defaults(self):
        identity = RoleStoryIdentity(
            story_name="test",
            story_personality_manifestation="brave",
            story_specific_goal="find treasure",
        )
        assert identity.story_key_items == []

    def test_full(self):
        identity = RoleStoryIdentity(
            story_name="Test Story",
            story_personality_manifestation="A cunning rogue",
            story_specific_goal="Steal the crown",
            story_key_items=["lockpick", "cloak"],
        )
        assert len(identity.story_key_items) == 2

    def test_json_serializable(self):
        identity = RoleStoryIdentity(
            story_name="test",
            story_personality_manifestation="brave",
            story_specific_goal="win",
        )
        data = identity.model_dump()
        assert data["story_name"] == "test"


class TestQualityReport:
    def test_defaults(self):
        report = QualityReport()
        assert report.status == "PASS"
        assert report.score == 0
        assert report.conflicts == []
        assert report.suggestions == []

    def test_fail_report(self):
        report = QualityReport(
            status="FAIL",
            score=3,
            conflicts=["role A contradicts role B"],
            suggestions=["re-generate role views"],
        )
        assert report.status == "FAIL"
        assert len(report.conflicts) == 1


class TestStoryState:
    def test_defaults(self):
        state = StoryState()
        assert state.story_id == "urban_detective"
        assert state.roles == []
        assert state.rag_enabled is True
        assert state.rag_top_k == 4
        assert state.max_retry == 1

    def test_event_callback_excluded(self):
        state = StoryState(event_callback=lambda e: None)
        dumped = state.model_dump()
        assert "event_callback" not in dumped

    def test_list_fields_are_independent(self):
        s1 = StoryState(roles=["A"])
        s2 = StoryState(roles=["B"])
        assert s1.roles == ["A"]
        assert s2.roles == ["B"]

    def test_dict_fields_are_independent(self):
        s1 = StoryState(role_view_drafts={"A": "text"})
        s2 = StoryState(role_view_drafts={"B": "text"})
        assert "B" not in s1.role_view_drafts
        assert "A" not in s2.role_view_drafts

    def test_model_dump_excludes_none_callbacks(self):
        state = StoryState()
        data = state.model_dump()
        assert "event_callback" not in data

    def test_quality_report_none_by_default(self):
        state = StoryState()
        assert state.quality_report is None
