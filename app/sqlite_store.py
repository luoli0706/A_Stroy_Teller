import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = Path(".data/story_teller.db")

def _get_conn(db_path: str):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(path))

def init_db(db_path: str = str(DEFAULT_DB_PATH)):
    """初始化数据库表结构。"""
    conn = _get_conn(db_path)
    try:
        with conn: # 自动处理 commit/rollback
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS story_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    style TEXT,
                    roles_json TEXT,
                    integrated_draft TEXT,
                    final_story TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS role_assets (
                    role_id TEXT PRIMARY KEY,
                    profile TEXT,
                    memory TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
    finally:
        conn.close()

def insert_story_run(topic: str, style: str, roles_json: str, integrated_draft: str, final_story: str, db_path: str) -> int:
    conn = _get_conn(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO story_runs (topic, style, roles_json, integrated_draft, final_story) VALUES (?, ?, ?, ?, ?)",
                (topic, style, roles_json, integrated_draft, final_story)
            )
            return cursor.lastrowid
    finally:
        conn.close()

def upsert_role_asset(role_id: str, profile: str, memory: str, db_path: str):
    conn = _get_conn(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO role_assets (role_id, profile, memory, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(role_id) DO UPDATE SET
                    profile=excluded.profile,
                    memory=excluded.memory,
                    updated_at=CURRENT_TIMESTAMP
            """, (role_id, profile, memory))
    finally:
        conn.close()

def list_story_runs(limit: int = 20, db_path: str = str(DEFAULT_DB_PATH)) -> List[Dict[str, Any]]:
    conn = _get_conn(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM story_runs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_story_run(run_id: int, db_path: str = str(DEFAULT_DB_PATH)) -> Optional[Dict[str, Any]]:
    conn = _get_conn(db_path)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM story_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
