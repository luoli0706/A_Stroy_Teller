from typing import Annotated, Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

class RoleStoryIdentity(BaseModel):
    """角色在特定故事中的身份设定。"""
    story_name: str
    story_personality_manifestation: str
    story_specific_goal: str
    story_key_items: List[str] = Field(default_factory=list)

class QualityReport(BaseModel):
    """结构化质检报告。"""
    status: str = "PASS" # PASS or FAIL
    score: int = 0
    conflicts: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

class StoryState(BaseModel):
    """[v0.3] 基于 Pydantic 的全局状态模型。"""
    
    # --- 输入参数 ---
    story_id: str = "urban_detective"
    topic: str = ""
    style: str = "suspense"
    roles: List[str] = Field(default_factory=list)
    max_retry: int = 1

    # --- 流程中间变量 ---
    retry_count: int = 0
    story_framework: str = ""
    role_assets: Dict[str, Dict[str, str]] = Field(default_factory=dict) # role_id -> {profile, memory}
    global_outline: str = ""

    # [v0.3] 既定事实时间线与世界观：由主线规划衍生，作为角色视角生成的权威参照
    established_facts: str = ""       # 按时间戳排列的关键事实列表（全角色共享的「客观」事件）
    world_bible: str = ""             # 世界观与背景设定，从框架 + 大纲中提炼

    # 角色映射与适配
    role_mapping: Dict[str, str] = Field(default_factory=dict) # Actor Name -> Slot Name
    role_story_identities: Dict[str, RoleStoryIdentity] = Field(default_factory=dict) # role_id -> Identity Model
    relationship_matrix: str = "" # [v0.2.3] 角色关系网描述

    # --- RAG 相关 ---
    rag_enabled: bool = True
    rag_top_k: int = 4
    rag_indexed_docs: int = 0
    rag_facts_indexed: int = 0        # [v0.3] 已索引的既定事实文档数
    rag_role_contexts: Dict[str, str] = Field(default_factory=dict) # role_id -> context_text（含既定事实检索结果）

    # --- 生成产物 ---
    role_view_drafts: Dict[str, str] = Field(default_factory=dict) # role_id -> text
    story_chapters: List[str] = Field(default_factory=list)    # [v0.3] 按章节整合的故事段落（化解上下文窗口问题）
    integrated_draft: str = ""
    quality_report: Optional[QualityReport] = None
    final_story: str = ""
    run_id: Optional[int] = None
    final_story_path: str = ""
    role_story_paths: Dict[str, str] = Field(default_factory=dict)
    memory_slice_paths: List[str] = Field(default_factory=list)

    # --- 系统/观测 ---
    logger_name: str = "story_teller"
    log_file_path: str = ""
    # 回调不参与模型序列化
    event_callback: Optional[Callable[[Dict[str, Any]], None]] = Field(None, exclude=True)

    class Config:
        arbitrary_types_allowed = True
