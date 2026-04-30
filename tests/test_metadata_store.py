"""元数据存储测试（含 filter key 白名单校验）。"""

import json
import pytest
from app.metadata_store import init_metadata_db, upsert_chunk, query_metadata, delete_by_source


SAMPLE_CHUNK = {
    "chunk_id": "test_story_RoleA_ch0",
    "role_id": "RoleA",
    "story_id": "test_story",
    "run_id": "1",
    "chapter_id": "1",
    "scene_id": "scene_0",
    "time_anchor": None,
    "location": "unknown",
    "entities": ["entity1", "entity2"],
    "props": ["prop1"],
    "narrative_type": "fact",
    "summary": "A test chunk summary...",
    "source_path": "/fake/path/test.md",
    "byte_offset_start": 0,
    "byte_offset_end": 100,
    "content_hash": "abc123",
    "parser_version": "v1.0",
}


class TestInit:
    def test_creates_tables_and_indexes(self, temp_metadata_db):
        import sqlite3
        conn = sqlite3.connect(str(temp_metadata_db))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "chunks" in tables
        conn.close()


class TestUpsertChunk:
    def test_insert(self, temp_metadata_db):
        upsert_chunk(dict(SAMPLE_CHUNK))
        results = query_metadata({"story_id": "test_story"}, limit=10)
        assert len(results) == 1
        assert results[0]["chunk_id"] == "test_story_RoleA_ch0"

    def test_update_on_conflict(self, temp_metadata_db):
        upsert_chunk(dict(SAMPLE_CHUNK))
        updated = dict(SAMPLE_CHUNK, summary="Updated summary...")
        upsert_chunk(updated)
        results = query_metadata({"chunk_id": "test_story_RoleA_ch0"}, limit=10)
        assert len(results) == 1
        assert results[0]["summary"] == "Updated summary..."

    def test_json_lists_roundtrip(self, temp_metadata_db):
        upsert_chunk(dict(SAMPLE_CHUNK))
        results = query_metadata({"chunk_id": "test_story_RoleA_ch0"}, limit=10)
        entities = json.loads(results[0]["entities"])
        assert entities == ["entity1", "entity2"]


class TestQueryMetadata:
    def test_single_filter(self, temp_metadata_db):
        upsert_chunk(dict(SAMPLE_CHUNK))
        results = query_metadata({"role_id": "RoleA"}, limit=10)
        assert len(results) == 1

    def test_list_filter(self, temp_metadata_db):
        upsert_chunk(dict(SAMPLE_CHUNK))
        upsert_chunk(dict(SAMPLE_CHUNK, chunk_id="test_story_RoleB_ch0", role_id="RoleB"))
        results = query_metadata({"role_id": ["RoleA", "RoleB"]}, limit=10)
        assert len(results) == 2

    def test_limit(self, temp_metadata_db):
        for i in range(5):
            upsert_chunk(dict(SAMPLE_CHUNK, chunk_id=f"test_story_RoleA_ch{i}"))
        results = query_metadata({"role_id": "RoleA"}, limit=3)
        assert len(results) == 3

    def test_invalid_filter_key_raises(self, temp_metadata_db):
        with pytest.raises(ValueError, match="Invalid filter key"):
            query_metadata({"malicious_key": "value"}, limit=10)

    def test_all_valid_keys_accepted(self, temp_metadata_db):
        valid_keys = [
            "story_id", "role_id", "run_id", "chapter_id", "scene_id",
            "time_anchor", "location", "narrative_type", "chunk_id",
            "content_hash", "parser_version", "source_path",
        ]
        for key in valid_keys:
            # 不应抛出异常
            query_metadata({key: "test"}, limit=1)


class TestDeleteBySource:
    def test_removes_chunks(self, temp_metadata_db):
        upsert_chunk(dict(SAMPLE_CHUNK))
        delete_by_source("/fake/path/test.md")
        results = query_metadata({"story_id": "test_story"}, limit=10)
        assert len(results) == 0
