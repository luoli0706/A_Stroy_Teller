from typing import TypedDict


class RoleAsset(TypedDict):
    profile: str
    memory: str


class StoryState(TypedDict, total=False):
    topic: str
    style: str
    roles: list[str]
    role_assets: dict[str, RoleAsset]
    global_outline: str
    role_view_drafts: dict[str, str]
    integrated_draft: str
    quality_report: str
    final_story: str
    run_id: int
    sqlite_db_path: str
