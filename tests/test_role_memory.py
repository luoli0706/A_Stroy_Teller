"""角色操作与路径遍历防护测试。"""

import pytest
from pathlib import Path
from app.role_memory import (
    _validate_id,
    discover_roles,
    load_role_assets,
    add_role_profile,
    delete_role_profile,
    add_role_memory_slice,
)


class TestValidateId:
    def test_valid_ids(self):
        _validate_id("Reshaely", "role_id")
        _validate_id("VanlyShan", "role_id")
        _validate_id("role_123", "role_id")
        _validate_id("my-role.name", "role_id")
        _validate_id("a", "role_id")

    def test_path_traversal_dots(self):
        with pytest.raises(ValueError, match="path separator"):
            _validate_id("../../../etc/passwd", "role_id")

    def test_path_traversal_slash(self):
        with pytest.raises(ValueError, match="path separator"):
            _validate_id("role/admin", "role_id")

    def test_path_traversal_backslash(self):
        with pytest.raises(ValueError, match="path separator"):
            _validate_id("role\\..\\..\\windows", "role_id")

    def test_invalid_chars(self):
        with pytest.raises(ValueError, match="Invalid role_id"):
            _validate_id("role name with spaces", "role_id")

    def test_empty(self):
        with pytest.raises(ValueError, match="Invalid role_id"):
            _validate_id("", "role_id")

    def test_too_long(self):
        long_id = "a" * 65
        with pytest.raises(ValueError, match="Invalid role_id"):
            _validate_id(long_id, "role_id")


class TestAddRoleProfile:
    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.role_memory.ROLE_DIR", tmp_path)
        path = add_role_profile("TestRole", "# Test Profile\nContent here")
        assert Path(path).exists()
        assert "profile.md" in path

    def test_traversal_guarded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.role_memory.ROLE_DIR", tmp_path)
        with pytest.raises(ValueError):
            add_role_profile("../../evil", "bad content")


class TestDeleteRoleProfile:
    def test_removes_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.role_memory.ROLE_DIR", tmp_path)
        add_role_profile("TempRole", "content")
        assert delete_role_profile("TempRole") is True
        assert not (tmp_path / "TempRole").exists()

    def test_nonexistent_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.role_memory.ROLE_DIR", tmp_path)
        assert delete_role_profile("NoSuchRole") is False


class TestAddRoleMemorySlice:
    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.role_memory.MEMORY_DIR", tmp_path)
        path = add_role_memory_slice("RoleA", "my_story", "## Chapter 1\nContent")
        assert Path(path).exists()

    def test_story_id_traversal_guarded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.role_memory.MEMORY_DIR", tmp_path)
        with pytest.raises(ValueError):
            add_role_memory_slice("RoleA", "../../etc", "content")


class TestDiscoverRoles:
    def test_empty_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.role_memory.ROLE_DIR", tmp_path)
        assert discover_roles(str(tmp_path)) == []

    def test_finds_directories(self, tmp_path, monkeypatch):
        (tmp_path / "RoleA").mkdir()
        (tmp_path / "RoleB").mkdir()
        (tmp_path / "not_a_role.txt").write_text("file")
        monkeypatch.setattr("app.role_memory.ROLE_DIR", tmp_path)
        roles = discover_roles(str(tmp_path))
        assert set(roles) == {"RoleA", "RoleB"}
