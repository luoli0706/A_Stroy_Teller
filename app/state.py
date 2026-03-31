from typing import Any
from typing import TypedDict


class RoleAsset(TypedDict):
    profile: str
    memory: str


class StoryState(TypedDict, total=False):
    logger_name: str
    log_file_path: str
    event_callback: Any
    story_id: str
    story_framework: str
    topic: str
    style: str
    roles: list[str]
    retry_count: int
    max_retry: int
    role_assets: dict[str, RoleAsset]
    global_outline: str
    role_view_drafts: dict[str, str]
    integrated_draft: str
    quality_report: str
    final_story: str
    run_id: int
    sqlite_db_path: str
