import json
import logging
import os
import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import (
    ROLE_DIR, MEMORY_DIR, STORIES_DIR, SQLITE_DB_PATH, 
    RAG_ENABLED, RAG_TOP_K, MAX_RETRY, OPT_STORIES_DIR
)
from app.llm_client import get_story_client
from app.rag.chroma_memory import (
    index_memory_directory,
    index_established_facts,
    persist_generated_role_slice,
)
from app.retrieval_tools import hybrid_search_async
from app.role_memory import discover_roles, load_role_assets
from app.sqlite_store import (
    init_db, create_placeholder_run, update_story_run, upsert_role_asset
)
from app.metadata_store import init_metadata_db
from app.state import StoryState, RoleStoryIdentity, QualityReport
from app.observability import log_event


def _emit_event(state: StoryState, event: dict) -> None:
    # 注意：在 astream_events 模式下，系统会自动捕获 token，
    # 但我们仍保留这个用于兼容旧逻辑或自定义事件。
    if state.event_callback:
        state.event_callback(event)


async def robust_task(coro, role_id: str, node_name: str, state: StoryState):
    try:
        return await coro
    except Exception as e:
        log_event(state.logger_name, f"Error in {node_name} for {role_id}: {str(e)}", logging.ERROR)
        return f"ERROR: Failed to execute {node_name}. {str(e)}"


async def collect_requirements(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, f"Node Start: collect_requirements | Topic: {state.topic}")
    init_db(str(SQLITE_DB_PATH))
    init_metadata_db()
    get_story_client().assert_ready()
    roles = state.roles if state.roles else discover_roles(str(ROLE_DIR))
    
    # [v0.3.0] 提前生成 run_id 以供后续索引使用
    run_id = create_placeholder_run(state.topic, state.style, json.dumps(roles), str(SQLITE_DB_PATH))
    log_event(state.logger_name, f"Created placeholder run, run_id={run_id}")
    
    return {
        "roles": roles,
        "run_id": run_id,
        "max_retry": state.max_retry or MAX_RETRY,
        "rag_enabled": state.rag_enabled if state.rag_enabled is not None else RAG_ENABLED,
        "rag_top_k": state.rag_top_k or RAG_TOP_K
    }


async def load_story_framework_node(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, f"Node Start: load_story_framework | ID: {state.story_id}")
    from app.story_framework import load_story_framework
    story_id, framework = load_story_framework(state.story_id, str(STORIES_DIR))
    return {"story_id": story_id, "story_framework": framework}


async def load_roles(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, f"Node Start: load_roles | Roles: {state.roles}")
    assets = load_role_assets(str(ROLE_DIR), state.roles, memory_dir=str(MEMORY_DIR))
    for rid, asset in assets.items():
        upsert_role_asset(rid, asset.get("profile", ""), asset.get("memory", ""), str(SQLITE_DB_PATH))
    return {"role_assets": assets}


async def index_role_memories_for_rag(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: index_role_memories_for_rag")
    if not state.rag_enabled:
        return {"rag_indexed_docs": 0}
    indexed = index_memory_directory(roles=state.roles)
    log_event(state.logger_name, f"RAG Incremental Indexed: {indexed} documents")
    return {"rag_indexed_docs": indexed}


async def map_roles_to_slots(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: map_roles_to_slots")
    client = get_story_client()
    profiles = {rid: asset.get("profile", "") for rid, asset in state.role_assets.items()}
    mapping_raw = await client.map_roles_to_slots_async(state.roles, profiles, state.story_framework)
    try:
        mapping = json.loads(mapping_raw)
    except:
        mapping = {rid: "Generic Role" for rid in state.roles}
    log_event(state.logger_name, f"Role Mapping Result: {mapping}")
    return {"role_mapping": mapping}


async def plan_global_story(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: plan_global_story (LLM Planning...)")
    client = get_story_client()
    outline = await client.plan_global_story_async(
        state.topic, state.style, state.role_mapping, state.story_framework, state.event_callback
    )
    log_event(state.logger_name, "Global Outline generated successfully.")
    return {"global_outline": outline}


async def generate_established_facts(state: StoryState) -> Dict[str, Any]:
    """[v0.3] 从全局大纲提炼既定事实时间线与世界观设定。"""
    log_event(state.logger_name, "Node Start: generate_established_facts (Extracting story ground truth...)")
    client = get_story_client()
    raw = await client.generate_established_facts_async(
        state.topic, state.style, state.global_outline, state.role_mapping, state.event_callback
    )

    # 将 LLM 输出切分为 established_facts 和 world_bible 两段
    facts_text = ""
    world_text = ""

    upper = raw.upper()
    facts_start = upper.find("ESTABLISHED FACTS")
    world_start = upper.find("WORLD BIBLE")

    if facts_start != -1 and world_start != -1:
        if facts_start < world_start:
            facts_text = raw[facts_start:world_start].strip()
            world_text = raw[world_start:].strip()
        else:
            world_text = raw[world_start:facts_start].strip()
            facts_text = raw[facts_start:].strip()
    else:
        # 无法识别分隔标记时，将全文作为 established_facts
        facts_text = raw.strip()

    log_event(state.logger_name, f"Established facts extracted ({len(facts_text)} chars), world bible ({len(world_text)} chars).")
    return {"established_facts": facts_text, "world_bible": world_text}


async def index_facts_for_rag(state: StoryState) -> Dict[str, Any]:
    """[v0.3] 将既定事实和世界观索引到向量库，供角色视角生成时检索。

    取代了「各角色在生成时 RAG 其他角色记忆切片」的旧策略，
    从根本上消除循环依赖：各角色统一从客观事实中取得上下文。
    """
    log_event(state.logger_name, "Node Start: index_facts_for_rag")
    if not state.rag_enabled or not state.established_facts:
        return {"rag_facts_indexed": 0}
    run_id = state.run_id or 0
    count = index_established_facts(
        state.story_id, run_id, state.established_facts, state.world_bible
    )
    log_event(state.logger_name, f"Facts RAG Indexed: {count} documents")
    return {"rag_facts_indexed": count}


async def wait_for_user_outline(state: StoryState) -> StoryState:
    log_event(state.logger_name, "Node: wait_for_user_outline (Checkpoint saved)")
    return state


async def adapt_roles_to_framework(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: adapt_roles_to_framework")
    client = get_story_client()
    tasks = []
    for rid in state.roles:
        profile = state.role_assets.get(rid, {}).get("profile", "")
        tasks.append(robust_task(
            client.adapt_role_to_framework_async(rid, profile, state.story_framework, state.global_outline, state.event_callback),
            rid, "adapt_roles", state
        ))
    results = await asyncio.gather(*tasks)
    identities = {}
    for rid, res in zip(state.roles, results):
        try:
            identities[rid] = RoleStoryIdentity.parse_raw(res)
        except:
            identities[rid] = RoleStoryIdentity(story_name=rid, story_personality_manifestation="As usual", story_specific_goal="Explore")
    
    rel_matrix = await client.generate_relationships_async(state.roles, {r: i.json() for r, i in identities.items()})
    log_event(state.logger_name, "Role identities adapted and relationship matrix generated.")
    return {"role_story_identities": identities, "relationship_matrix": rel_matrix}


async def retrieve_role_rag_contexts(state: StoryState) -> Dict[str, Any]:
    """[v0.3] 为每个角色检索 RAG 上下文。

    新策略：使用 hybrid_search_async 统一检索。
    混合检索将同时覆盖该角色的专属记忆以及代表客观锚点的既定事实 (__facts__) 和世界观 (__world__)。
    """
    log_event(state.logger_name, "Node Start: retrieve_role_rag_contexts (Hybrid)")
    if not state.rag_enabled:
        return {"rag_role_contexts": {}}

    query_text = f"Topic: {state.topic}"
    
    tasks = []
    for rid in state.roles:
        # 为每个角色检索：私有记忆 + 既定事实 + 世界观
        tasks.append(hybrid_search_async(
            state.story_id, 
            query_text, 
            filters={"role_id": [rid, "__facts__", "__world__"]},
            limit=state.rag_top_k
        ))

    results = await asyncio.gather(*tasks)
    return {"rag_role_contexts": dict(zip(state.roles, results))}


async def generate_role_views(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: generate_role_views (Parallel LLM Generation...)")
    client = get_story_client()
    tasks = []
    for rid in state.roles:
        asset = state.role_assets.get(rid, {})
        identity = state.role_story_identities.get(rid, RoleStoryIdentity(story_name=rid, story_personality_manifestation="", story_specific_goal="")).json()
        tasks.append(robust_task(
            client.generate_role_view_async(
                rid, asset.get("profile", ""), identity, state.relationship_matrix,
                asset.get("memory", ""), state.rag_role_contexts.get(rid, ""),
                state.global_outline, state.style, state.event_callback
            ),
            rid, "generate_role_views", state
        ))
    results = await asyncio.gather(*tasks)
    log_event(state.logger_name, "All role views generated.")
    return {"role_view_drafts": dict(zip(state.roles, results))}


async def integrate_perspectives(state: StoryState) -> Dict[str, Any]:
    """[v0.3] 整合多角色叙事。

    新策略：若存在既定事实，则调用 integrate_by_chapters_async 按章节整合，
    利用既定事实作为各章节的锚点，分批次发送给 LLM，有效化解上下文窗口压力。
    """
    log_event(state.logger_name, "Node Start: integrate_perspectives")
    client = get_story_client()
    integrated = await client.integrate_perspectives_async(
        state.topic, state.style, state.role_view_drafts, state.event_callback,
        established_facts=state.established_facts,
    )
    # 将章节列表存入 story_chapters（按 ## Chapter N 分割）
    chapters = [c.strip() for c in integrated.split("\n\n## Chapter ") if c.strip()]
    return {"integrated_draft": integrated, "story_chapters": chapters}


async def quality_check(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: quality_check")
    client = get_story_client()
    report_raw = await client.quality_check_async(state.global_outline, state.integrated_draft, state.roles, state.event_callback)
    try:
        report = QualityReport.parse_raw(report_raw)
    except:
        report = QualityReport(status="FAIL", conflicts=["Invalid JSON from QA"])
    new_retry = state.retry_count + (1 if report.status == "FAIL" else 0)
    log_event(state.logger_name, f"Quality Report: {report.status} (Score: {report.score})")
    return {"quality_report": report, "retry_count": new_retry}


def route_after_quality(state: StoryState) -> str:
    if state.quality_report and state.quality_report.status == "FAIL" and state.retry_count <= state.max_retry:
        return "generate_role_views"
    return "finalize_output"


async def finalize_output(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: finalize_output (Persisting Results...)")
    final_story = state.integrated_draft
    run_id = state.run_id
    update_story_run(run_id, final_story, final_story, str(SQLITE_DB_PATH))
    
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    role_story_paths = {}
    for rid, content in state.role_view_drafts.items():
        p = persist_generated_role_slice(rid, state.story_id, run_id, ts, state.topic, state.style, content)
        role_story_paths[rid] = str(p)
    
    story_opt_dir = OPT_STORIES_DIR / state.story_id / "final"
    story_opt_dir.mkdir(parents=True, exist_ok=True)
    out_file = story_opt_dir / f"final_run_{run_id}.md"
    out_file.write_text(f"# {state.topic}\n\n{final_story}", encoding="utf-8")
    
    log_event(state.logger_name, f"Final story saved to: {out_file}")
    return {
        "final_story": final_story,
        "run_id": run_id,
        "final_story_path": str(out_file),
        "role_story_paths": role_story_paths,
        "memory_slice_paths": list(role_story_paths.values()),
    }


async def distill_memories(state: StoryState) -> Dict[str, Any]:
    log_event(state.logger_name, "Node Start: distill_memories")
    for rid, content in state.role_view_drafts.items():
        summary_path = MEMORY_DIR / rid / f"{rid}_summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n### Chapter Run {state.run_id} ({datetime.now().isoformat()})\n{content.strip()}\n")
    log_event(state.logger_name, "Memory distillation complete.")
    return {}


def build_graph(checkpointer: Any = None):
    graph = StateGraph(StoryState)
    
    nodes = [
        ("collect_requirements", collect_requirements),
        ("load_story_framework", load_story_framework_node),
        ("load_roles", load_roles),
        ("index_role_memories_for_rag", index_role_memories_for_rag),
        ("map_roles_to_slots", map_roles_to_slots),
        ("plan_global_story", plan_global_story),
        # [v0.3] 新增：从大纲提炼既定事实时间线与世界观
        ("generate_established_facts", generate_established_facts),
        # [v0.3] 新增：将既定事实索引到向量库，供角色视角生成时检索
        ("index_facts_for_rag", index_facts_for_rag),
        ("wait_for_user_outline", wait_for_user_outline),
        ("adapt_roles_to_framework", adapt_roles_to_framework),
        ("retrieve_role_rag_contexts", retrieve_role_rag_contexts),
        ("generate_role_views", generate_role_views),
        ("integrate_perspectives", integrate_perspectives),
        ("quality_check", quality_check),
        ("finalize_output", finalize_output),
        ("distill_memories", distill_memories),
    ]
    for name, func in nodes:
        graph.add_node(name, func)

    graph.add_edge(START, "collect_requirements")
    graph.add_edge("collect_requirements", "load_story_framework")
    graph.add_edge("load_story_framework", "load_roles")
    graph.add_edge("load_roles", "index_role_memories_for_rag")
    graph.add_edge("index_role_memories_for_rag", "map_roles_to_slots")
    graph.add_edge("map_roles_to_slots", "plan_global_story")
    # [v0.3] plan_global_story -> generate_established_facts -> index_facts_for_rag -> wait_for_user_outline
    graph.add_edge("plan_global_story", "generate_established_facts")
    graph.add_edge("generate_established_facts", "index_facts_for_rag")
    graph.add_edge("index_facts_for_rag", "wait_for_user_outline")
    graph.add_edge("wait_for_user_outline", "adapt_roles_to_framework")
    graph.add_edge("adapt_roles_to_framework", "retrieve_role_rag_contexts")
    graph.add_edge("retrieve_role_rag_contexts", "generate_role_views")
    graph.add_edge("generate_role_views", "integrate_perspectives")
    graph.add_edge("integrate_perspectives", "quality_check")
    graph.add_conditional_edges("quality_check", route_after_quality, {
        "generate_role_views": "generate_role_views",
        "finalize_output": "finalize_output"
    })
    graph.add_edge("finalize_output", "distill_memories")
    graph.add_edge("distill_memories", END)

    return graph.compile(checkpointer=checkpointer)
