from typing import Annotated, Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

class RoleStoryIdentity(BaseModel):
    """角色在特定故事中的身份设定。"""
    story_name: str
    story_personality_manifestation: str
    story_specific_goal: str
    story_key_items: List[str] = []

class QualityReport(BaseModel):
    """结构化质检报告。"""
    status: str = "PASS" # PASS or FAIL
    score: int = 0
    conflicts: List[str] = []
    suggestions: List[str] = []

class StoryState(BaseModel):
    """[v0.2.3] 基于 Pydantic 的全局状态模型。"""
    
    # --- 输入参数 ---
    story_id: str = "urban_detective"
    topic: str = ""
    style: str = "suspense"
    roles: List[str] = []
    max_retry: int = 1

    # --- 流程中间变量 ---
    retry_count: int = 0
    story_framework: str = ""
    role_assets: Dict[str, Dict[str, str]] = {} # role_id -> {profile, memory}
    global_outline: str = ""
    
    # 角色映射与适配
    role_mapping: Dict[str, str] = {} # Actor Name -> Slot Name
    role_story_identities: Dict[str, RoleStoryIdentity] = {} # role_id -> Identity Model
    relationship_matrix: str = "" # [v0.2.3] 角色关系网描述

    # --- RAG 相关 ---
    rag_enabled: bool = True
    rag_top_k: int = 4
    rag_indexed_docs: int = 0
    rag_role_contexts: Dict[str, str] = {} # role_id -> context_text

    # --- 生成产物 ---
    role_view_drafts: Dict[str, str] = {} # role_id -> text
    integrated_draft: str = ""
    quality_report: Optional[QualityReport] = None
    final_story: str = ""
    run_id: Optional[int] = None
    final_story_path: str = ""
    role_story_paths: Dict[str, str] = {}
    memory_slice_paths: List[str] = []

    # --- 系统/观测 ---
    logger_name: str = "story_teller"
    log_file_path: str = ""
    # 回调不参与模型序列化
    event_callback: Optional[Callable[[Dict[str, Any]], None]] = Field(None, exclude=True)

    class Config:
        arbitrary_types_allowed = True
