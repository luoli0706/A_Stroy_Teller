import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(".data/story_teller.db")


def _ensure_parent_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _get_connection(db_path: Path) -> sqlite3.Connection:
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> str:
    path = Path(db_path)
    with _get_connection(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS role_assets (
                role_id TEXT PRIMARY KEY,
                profile TEXT NOT NULL DEFAULT '',
                memory TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS story_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                style TEXT NOT NULL,
                roles_json TEXT NOT NULL,
                integrated_draft TEXT NOT NULL,
                final_story TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    return str(path)


def upsert_role_asset(
    role_id: str,
    profile: str,
    memory: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    path = Path(db_path)
    with _get_connection(path) as conn:
        conn.execute(
            """
            INSERT INTO role_assets (role_id, profile, memory)
            VALUES (?, ?, ?)
            ON CONFLICT(role_id) DO UPDATE SET
                profile=excluded.profile,
                memory=excluded.memory,
                updated_at=CURRENT_TIMESTAMP
            """,
            (role_id, profile, memory),
        )
        conn.commit()


def insert_story_run(
    topic: str,
    style: str,
    roles_json: str,
    integrated_draft: str,
    final_story: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    path = Path(db_path)
    with _get_connection(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO story_runs (topic, style, roles_json, integrated_draft, final_story)
            VALUES (?, ?, ?, ?, ?)
            """,
            (topic, style, roles_json, integrated_draft, final_story),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_story_runs(
    limit: int = 30,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict]:
    path = Path(db_path)
    with _get_connection(path) as conn:
        cur = conn.execute(
            """
            SELECT id, topic, style, roles_json, created_at
            FROM story_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_story_run(
    run_id: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict | None:
    path = Path(db_path)
    with _get_connection(path) as conn:
        cur = conn.execute(
            """
            SELECT id, topic, style, roles_json, integrated_draft, final_story, created_at
            FROM story_runs
            WHERE id = ?
            """,
            (run_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None
    return dict(row)