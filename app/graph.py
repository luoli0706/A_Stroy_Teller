import json
import logging
import os
import asyncio
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from langgraph.graph import END, START, StateGraph

from app.config import (
    ROLE_DIR, MEMORY_DIR, STORIES_DIR, SQLITE_DB_PATH, 
    RAG_ENABLED, RAG_TOP_K, MAX_RETRY, OPT_STORIES_DIR
)
from app.llm_client import get_story_client
from app.rag.chroma_memory import (
    format_role_rag_context_async,
    index_memory_directory,
    persist_generated_role_slice,
)
from app.role_memory import discover_roles, load_role_assets
from app.sqlite_store import init_db, insert_story_run, upsert_role_asset
from app.state import StoryState, RoleStoryIdentity, QualityReport


def _get_logger(state: StoryState) -> logging.Logger:
    return logging.getLogger(state.logger_name)


def _emit_event(state: StoryState, event: dict) -> None:
    if state.event_callback:
        state.event_callback(event)


async def robust_task(coro, role_id: str, node_name: str, state: StoryState):
    """[v0.2.3] 并发容错包装器。"""
    try:
        return await coro
    except Exception as e:
        _get_logger(state).error(f"Error in {node_name} for {role_id}: {str(e)}")
        _emit_event(state, {"event": "error", "node": node_name, "role_id": role_id, "message": str(e)})
        return f"ERROR: Failed to execute {node_name}. {str(e)}"


async def collect_requirements(state: StoryState) -> Dict[str, Any]:
    init_db(str(SQLITE_DB_PATH))
    get_story_client().assert_ready()
    
    # 填充默认值
    roles = state.roles if state.roles else discover_roles(str(ROLE_DIR))
    return {
        "roles": roles,
        "max_retry": state.max_retry or MAX_RETRY,
        "rag_enabled": state.rag_enabled if state.rag_enabled is not None else RAG_ENABLED,
        "rag_top_k": state.rag_top_k or RAG_TOP_K
    }


async def load_story_framework_node(state: StoryState) -> Dict[str, Any]:
    from app.story_framework import load_story_framework
    story_id, framework = load_story_framework(state.story_id, str(STORIES_DIR))
    return {"story_id": story_id, "story_framework": framework}


async def load_roles(state: StoryState) -> Dict[str, Any]:
    assets = load_role_assets(str(ROLE_DIR), state.roles, memory_dir=str(MEMORY_DIR))
    for rid, asset in assets.items():
        upsert_role_asset(rid, asset.get("profile", ""), asset.get("memory", ""), str(SQLITE_DB_PATH))
    return {"role_assets": assets}


async def index_role_memories_for_rag(state: StoryState) -> Dict[str, Any]:
    if not state.rag_enabled:
        return {"rag_indexed_docs": 0}
    indexed = index_memory_directory(roles=state.roles)
    return {"rag_indexed_docs": indexed}


async def map_roles_to_slots(state: StoryState) -> Dict[str, Any]:
    """[v0.2.3] 独立的角色分配节点。"""
    client = get_story_client()
    profiles = {rid: asset.get("profile", "") for rid, asset in state.role_assets.items()}
    mapping_raw = await client.map_roles_to_slots_async(state.roles, profiles, state.story_framework)
    try:
        mapping = json.loads(mapping_raw)
    except:
        mapping = {rid: "Generic Role" for rid in state.roles}
    return {"role_mapping": mapping}


async def plan_global_story(state: StoryState) -> Dict[str, Any]:
    client = get_story_client()
    outline = await client.plan_global_story_async(
        state.topic, state.style, state.role_mapping, state.story_framework, state.event_callback
    )
    return {"global_outline": outline}


async def adapt_roles_to_framework(state: StoryState) -> Dict[str, Any]:
    """[v0.2.3] 容错并发适配。"""
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
    
    # 同时生成关系网
    rel_matrix = await client.generate_relationships_async(state.roles, {r: i.json() for r, i in identities.items()})
    return {"role_story_identities": identities, "relationship_matrix": rel_matrix}


async def retrieve_role_rag_contexts(state: StoryState) -> Dict[str, Any]:
    if not state.rag_enabled:
        return {"rag_role_contexts": {}}
    tasks = [format_role_rag_context_async(state.story_id, rid, state.roles, f"Topic: {state.topic}", state.rag_top_k) for rid in state.roles]
    results = await asyncio.gather(*tasks)
    return {"rag_role_contexts": dict(zip(state.roles, results))}


async def generate_role_views(state: StoryState) -> Dict[str, Any]:
    """[v0.2.3] 容错并发生成。"""
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
    return {"role_view_drafts": dict(zip(state.roles, results))}


async def integrate_perspectives(state: StoryState) -> Dict[str, Any]:
    client = get_story_client()
    integrated = await client.integrate_perspectives_async(state.topic, state.style, state.role_view_drafts, state.event_callback)
    return {"integrated_draft": integrated}


async def quality_check(state: StoryState) -> Dict[str, Any]:
    client = get_story_client()
    report_raw = await client.quality_check_async(state.global_outline, state.integrated_draft, state.roles, state.event_callback)
    try:
        report = QualityReport.parse_raw(report_raw)
    except:
        report = QualityReport(status="FAIL", conflicts=["Invalid JSON from QA"])
    
    new_retry = state.retry_count + (1 if report.status == "FAIL" else 0)
    return {"quality_report": report, "retry_count": new_retry}


def route_after_quality(state: StoryState) -> str:
    if state.quality_report and state.quality_report.status == "FAIL" and state.retry_count <= state.max_retry:
        return "generate_role_views"
    return "finalize_output"


async def finalize_output(state: StoryState) -> Dict[str, Any]:
    run_id = insert_story_run(state.topic, state.style, json.dumps(state.roles), state.integrated_draft, state.integrated_draft, str(SQLITE_DB_PATH))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    paths = []
    for rid, content in state.role_view_drafts.items():
        p = persist_generated_role_slice(rid, state.story_id, run_id, ts, state.topic, state.style, content)
        paths.append(str(p))
    return {"final_story": state.integrated_draft, "run_id": run_id, "memory_slice_paths": paths}


async def distill_memories(state: StoryState) -> Dict[str, Any]:
    """[v0.2.3] 改进的记忆蒸馏：追加到汇总。后续可加 LLM 压缩。"""
    for rid, content in state.role_view_drafts.items():
        summary_path = MEMORY_DIR / rid / f"{rid}_summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n### Chapter Run {state.run_id} ({datetime.now().isoformat()})\n{content.strip()}\n")
    return {}


def build_graph():
    # 注意：Pydantic 模型在 LangGraph 中通常作为 Dict 处理，或者在节点中转换
    graph = StateGraph(StoryState)
    
    nodes = [
        ("collect_requirements", collect_requirements),
        ("load_story_framework", load_story_framework_node),
        ("load_roles", load_roles),
        ("index_role_memories_for_rag", index_role_memories_for_rag),
        ("map_roles_to_slots", map_roles_to_slots),
        ("plan_global_story", plan_global_story),
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
    graph.add_edge("plan_global_story", "adapt_roles_to_framework")
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
    return graph.compile()
