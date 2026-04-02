import json
import logging
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path

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
from app.state import StoryState
from app.story_framework import DEFAULT_STORY_ID, load_story_framework


def _get_logger(state: StoryState) -> logging.Logger:
    return logging.getLogger(state.get("logger_name", "story_teller"))


def _emit_event(state: StoryState, event: dict) -> None:
    callback = state.get("event_callback")
    if callable(callback):
        callback(event)


async def collect_requirements(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=collect_requirements status=start")
    story_id = state.get("story_id", DEFAULT_STORY_ID)
    roles = state.get("roles") or discover_roles(str(ROLE_DIR))
    init_db(str(SQLITE_DB_PATH))
    get_story_client().assert_ready()
    return {
        **state,
        "story_id": story_id,
        "roles": roles,
        "retry_count": state.get("retry_count", 0),
        "max_retry": state.get("max_retry", MAX_RETRY),
        "rag_enabled": state.get("rag_enabled", RAG_ENABLED),
        "rag_top_k": state.get("rag_top_k", RAG_TOP_K),
    }


async def load_story_framework_node(state: StoryState) -> StoryState:
    story_id, framework = load_story_framework(
        story_id=state.get("story_id", DEFAULT_STORY_ID),
        stories_dir=str(STORIES_DIR),
    )
    return {**state, "story_id": story_id, "story_framework": framework}


async def load_roles(state: StoryState) -> StoryState:
    roles = state.get("roles", [])
    assets = load_role_assets(str(ROLE_DIR), roles, memory_dir=str(MEMORY_DIR))
    for role_id, role_asset in assets.items():
        upsert_role_asset(
            role_id=role_id,
            profile=role_asset.get("profile", ""),
            memory=role_asset.get("memory", ""),
            db_path=str(SQLITE_DB_PATH),
        )
    return {**state, "role_assets": assets}


async def index_role_memories_for_rag(state: StoryState) -> StoryState:
    if not state.get("rag_enabled"):
        return {**state, "rag_indexed_docs": 0}
    indexed = index_memory_directory(roles=state.get("roles", []))
    _emit_event(state, {"event": "node_log", "node": "index", "message": f"RAG Indexed: {indexed}"})
    return {**state, "rag_indexed_docs": indexed}


async def plan_global_story(state: StoryState) -> StoryState:
    client = get_story_client()
    outline = await client.plan_global_story_async(
        topic=state["topic"],
        style=state["style"],
        role_ids=state.get("roles", []),
        framework=state.get("story_framework", ""),
        token_callback=state.get("event_callback"),
    )
    return {**state, "global_outline": outline}


async def wait_for_user_outline(state: StoryState) -> StoryState:
    """[Alpha 0.2] HITL 中断点：等待用户确认/编辑大纲。"""
    _emit_event(state, {"event": "node_log", "node": "wait_for_user_outline", "message": "Outline ready. Waiting for user confirmation..."})
    # 在实际运行中，LangGraph 的 interrupt(outline) 会在此挂起
    return state


async def retrieve_role_rag_contexts(state: StoryState) -> StoryState:
    if not state.get("rag_enabled"):
        return {**state, "rag_role_contexts": {}}
    story_id = state.get("story_id")
    roles = state.get("roles", [])
    top_k = state.get("rag_top_k")
    tasks = [format_role_rag_context_async(story_id, rid, roles, f"Topic: {state.get('topic')}", top_k) for rid in roles]
    results = await asyncio.gather(*tasks)
    return {**state, "rag_role_contexts": dict(zip(roles, results))}


async def generate_role_views(state: StoryState) -> StoryState:
    client = get_story_client()
    roles = state.get("roles", [])
    role_assets = state.get("role_assets", {})
    rag_contexts = state.get("rag_role_contexts", {})
    tasks = []
    for rid in roles:
        asset = role_assets.get(rid, {"profile": "", "memory": ""})
        tasks.append(client.generate_role_view_async(
            role_id=rid, profile=asset["profile"], memory=asset["memory"],
            rag_context=rag_contexts.get(rid, ""), outline=state["global_outline"],
            style=state["style"], token_callback=state.get("event_callback"),
        ))
    results = await asyncio.gather(*tasks)
    return {**state, "role_view_drafts": dict(zip(roles, results))}


async def integrate_perspectives(state: StoryState) -> StoryState:
    client = get_story_client()
    integrated = await client.integrate_perspectives_async(
        topic=state.get("topic", ""),
        style=state.get("style", ""),
        role_drafts=state.get("role_view_drafts", {}),
        token_callback=state.get("event_callback"),
    )
    return {**state, "integrated_draft": integrated}


async def quality_check(state: StoryState) -> StoryState:
    """[Alpha 0.2] 结构化质检。"""
    client = get_story_client()
    report_raw = await client.quality_check_async(
        outline=state.get("global_outline", ""),
        integrated_story=state.get("integrated_draft", ""),
        role_ids=state.get("roles", []),
        token_callback=state.get("event_callback"),
    )
    try:
        report = json.loads(report_raw)
    except Exception:
        report = {"status": "FAIL", "score": 0, "conflicts": ["Invalid JSON output from QA model"]}
    
    retry_count = state.get("retry_count", 0)
    if report.get("status") == "FAIL":
        retry_count += 1
    return {**state, "quality_report": json.dumps(report, ensure_ascii=False), "retry_count": retry_count}


def route_after_quality(state: StoryState) -> str:
    report = json.loads(state.get("quality_report", '{"status": "PASS"}'))
    if report.get("status") == "FAIL" and state.get("retry_count", 0) <= state.get("max_retry", 1):
        return "generate_role_views"
    return "finalize_output"


async def finalize_output(state: StoryState) -> StoryState:
    final_story = state.get("integrated_draft", "")
    run_id = insert_story_run(
        topic=state.get("topic", ""),
        style=state.get("style", ""),
        roles_json=json.dumps(state.get("roles", [])),
        integrated_draft=state.get("integrated_draft", ""),
        final_story=final_story,
        db_path=str(SQLITE_DB_PATH),
    )
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    memory_slice_paths = []
    for rid, content in state.get("role_view_drafts", {}).items():
        path = persist_generated_role_slice(
            role_id=rid, story_id=state["story_id"], run_id=run_id,
            chapter_timestamp=ts, topic=state["topic"], style=state["style"],
            content=content
        )
        memory_slice_paths.append(str(path))
    
    story_opt_dir = OPT_STORIES_DIR / state["story_id"]
    story_opt_dir.mkdir(exist_ok=True)
    (story_opt_dir / f"final_run_{run_id}.md").write_text(f"# {state['topic']}\n\n{final_story}", encoding="utf-8")

    return {**state, "final_story": final_story, "run_id": run_id, "memory_slice_paths": memory_slice_paths}


async def distill_memories(state: StoryState) -> StoryState:
    """[Alpha 0.2] 记忆蒸馏节点：自动汇总本次生成的角色切片到长期记忆汇总。"""
    # 逻辑简化：仅将本次生成内容追加到汇总，Alpha 0.3 将引入 LLM 总结
    for rid, content in state.get("role_view_drafts", {}).items():
        summary_path = MEMORY_DIR / rid / f"{rid}_summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n### Chapter Run {state.get('run_id')}\n{content.strip()}\n")
    return state


def build_graph():
    graph = StateGraph(StoryState)
    nodes = [
        ("collect_requirements", collect_requirements),
        ("load_story_framework", load_story_framework_node),
        ("load_roles", load_roles),
        ("index_role_memories_for_rag", index_role_memories_for_rag),
        ("plan_global_story", plan_global_story),
        ("wait_for_user_outline", wait_for_user_outline),
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
    graph.add_edge("index_role_memories_for_rag", "plan_global_story")
    graph.add_edge("plan_global_story", "wait_for_user_outline")
    graph.add_edge("wait_for_user_outline", "retrieve_role_rag_contexts")
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
