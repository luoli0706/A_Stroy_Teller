"""SQLite 存储操作测试。"""

import json
import pytest
from app.sqlite_store import (
    init_db,
    create_placeholder_run,
    update_story_run,
    insert_story_run,
    upsert_role_asset,
    list_story_runs,
    get_story_run,
)


class TestInitDb:
    def test_creates_tables(self, temp_db):
        init_db(temp_db)
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "story_runs" in tables
        assert "role_assets" in tables
        conn.close()

    def test_idempotent(self, temp_db):
        init_db(temp_db)
        init_db(temp_db)  # 不应抛出异常


class TestStoryRuns:
    def test_create_placeholder(self, temp_db):
        init_db(temp_db)
        run_id = create_placeholder_run("test topic", "suspense", json.dumps(["A", "B"]), temp_db)
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_create_placeholder_returns_increasing_ids(self, temp_db):
        init_db(temp_db)
        id1 = create_placeholder_run("t1", "s1", '["A"]', temp_db)
        id2 = create_placeholder_run("t2", "s2", '["B"]', temp_db)
        assert id2 > id1

    def test_update_story_run(self, temp_db):
        init_db(temp_db)
        run_id = create_placeholder_run("topic", "style", '["A"]', temp_db)
        update_story_run(run_id, "draft content", "final story", temp_db)
        record = get_story_run(run_id, temp_db)
        assert record is not None
        assert record["integrated_draft"] == "draft content"
        assert record["final_story"] == "final story"

    def test_insert_story_run(self, temp_db):
        init_db(temp_db)
        run_id = insert_story_run("topic", "style", '["X"]', "draft", "final", temp_db)
        assert isinstance(run_id, int)

    def test_get_nonexistent_run(self, temp_db):
        init_db(temp_db)
        assert get_story_run(99999, temp_db) is None

    def test_list_story_runs_order(self, temp_db):
        init_db(temp_db)
        insert_story_run("first", "s", '[]', "", "", temp_db)
        insert_story_run("second", "s", '[]', "", "", temp_db)
        runs = list_story_runs(limit=10, db_path=temp_db)
        assert len(runs) >= 2
        # 最新的在前
        assert runs[0]["topic"] == "second"


class TestRoleAssets:
    def test_upsert_insert(self, temp_db):
        init_db(temp_db)
        upsert_role_asset("RoleA", "profile text", "memory text", temp_db)
        import sqlite3
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM role_assets WHERE role_id = ?", ("RoleA",)).fetchone()
        assert row is not None
        assert row["profile"] == "profile text"
        conn.close()

    def test_upsert_update(self, temp_db):
        init_db(temp_db)
        upsert_role_asset("RoleA", "old profile", "old memory", temp_db)
        upsert_role_asset("RoleA", "new profile", "new memory", temp_db)
        import sqlite3
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM role_assets WHERE role_id = ?", ("RoleA",)).fetchone()
        assert row["profile"] == "new profile"
        conn.close()
