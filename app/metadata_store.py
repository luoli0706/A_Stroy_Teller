import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import METADATA_DB_PATH

def _get_conn():
    METADATA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(METADATA_DB_PATH))
    # 开启 WAL 模式以提高并发性能
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_metadata_db():
    """初始化元数据数据库。"""
    conn = _get_conn()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id TEXT UNIQUE,
                    role_id TEXT,
                    story_id TEXT,
                    run_id TEXT,
                    chapter_id TEXT,
                    scene_id TEXT,
                    time_anchor TEXT,
                    location TEXT,
                    entities TEXT, -- JSON array
                    props TEXT,    -- JSON array
                    narrative_type TEXT, -- fact/world/dialogue/inner_monologue
                    summary TEXT,
                    source_path TEXT,
                    byte_offset_start INTEGER,
                    byte_offset_end INTEGER,
                    content_hash TEXT,
                    parser_version TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_story_role ON chunks(story_id, role_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_story_chapter ON chunks(story_id, chapter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_narrative_type ON chunks(narrative_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_content_hash ON chunks(content_hash)")
    finally:
        conn.close()

def upsert_chunk(chunk_data: Dict[str, Any]):
    """插入或更新 Chunk 元数据。"""
    conn = _get_conn()
    try:
        # 转换列表为 JSON 字符串
        for key in ["entities", "props"]:
            if key in chunk_data and isinstance(chunk_data[key], list):
                chunk_data[key] = json.dumps(chunk_data[key], ensure_ascii=False)
        
        fields = [
            "chunk_id", "role_id", "story_id", "run_id", "chapter_id", "scene_id",
            "time_anchor", "location", "entities", "props", "narrative_type",
            "summary", "source_path", "byte_offset_start", "byte_offset_end",
            "content_hash", "parser_version"
        ]
        
        placeholders = ", ".join(["?"] * len(fields))
        update_stmt = ", ".join([f"{f}=excluded.{f}" for f in fields if f != "chunk_id"])
        
        query = f"""
            INSERT INTO chunks ({", ".join(fields)})
            VALUES ({placeholders})
            ON CONFLICT(chunk_id) DO UPDATE SET
                {update_stmt},
                updated_at=CURRENT_TIMESTAMP
        """
        
        params = [chunk_data.get(f) for f in fields]
        
        with conn:
            conn.execute(query, params)
    finally:
        conn.close()

def query_metadata(filters: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
    """查询元数据，支持单个值或列表（IN 子句）。"""
    conn = _get_conn()
    try:
        where_clauses = []
        params = []
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    placeholders = ", ".join(["?"] * len(value))
                    where_clauses.append(f"{key} IN ({placeholders})")
                    params.extend(value)
                else:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
        
        query = "SELECT * FROM chunks"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def delete_by_source(source_path: str):
    """删除指定来源路径的所有元数据（用于更新文件前清理）。"""
    conn = _get_conn()
    try:
        with conn:
            conn.execute("DELETE FROM chunks WHERE source_path = ?", (source_path,))
    finally:
        conn.close()
