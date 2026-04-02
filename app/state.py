from typing import Annotated, Any, Callable, TypedDict


def _merge_dict(left: dict, right: dict) -> dict:
    return {**left, **right}


class StoryState(TypedDict):
    """LangGraph 状态定义。"""

    # --- 输入参数 ---
    story_id: str
    topic: str
    style: str
    roles: list[str]
    max_retry: int

    # --- 流程中间变量 ---
    retry_count: int
    story_framework: str
    role_assets: dict[str, dict]  # role_id -> {profile, memory}
    global_outline: str
    
    # [v0.2.2] 角色在当前故事中的特定设定: role_id -> json_str
    role_story_identities: dict[str, str]

    # --- RAG 相关 ---
    rag_enabled: bool
    rag_top_k: int
    rag_indexed_docs: int
    rag_role_contexts: dict[str, str]  # role_id -> context_text

    # --- 生成产物 ---
    role_view_drafts: dict[str, str]  # role_id -> text
    integrated_draft: str
    quality_report: str  # JSON 格式
    final_story: str
    run_id: int
    memory_slice_paths: list[str]

    # --- 系统/观测 ---
    logger_name: str
    log_file_path: str
    # 允许在运行时注入回调，用于 UI 实时更新
    event_callback: Annotated[Callable[[dict[str, Any]], None], "callback"]
