import json
import logging
import os
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph

from app.llm_client import get_story_client
from app.rag.chroma_memory import (
    format_role_rag_context,
    index_memory_directory,
    persist_generated_role_slice,
)
from app.role_memory import discover_roles, load_role_assets
from app.sqlite_store import DEFAULT_DB_PATH, init_db, insert_story_run, upsert_role_asset
from app.state import StoryState
from app.story_framework import DEFAULT_STORY_ID, load_story_framework


ROLE_DIR = "role"
MEMORY_DIR = "memory"
STORIES_DIR = "stories"


def _env_flag(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get_logger(state: StoryState) -> logging.Logger:
    logger_name = state.get("logger_name", "story_teller")
    return logging.getLogger(logger_name)


def _emit_event(state: StoryState, event: dict) -> None:
    callback = state.get("event_callback")
    if callable(callback):
        callback(event)


def collect_requirements(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=collect_requirements stage=start pid=%s", os.getpid())
    max_retry = int(state.get("max_retry", os.getenv("MAX_RETRY", "1")))
    story_id = state.get("story_id", DEFAULT_STORY_ID)
    topic = state.get("topic", "an unexpected friendship")
    style = state.get("style", "warm")
    roles = state.get("roles") or discover_roles(ROLE_DIR)
    sqlite_db_path = state.get("sqlite_db_path") or str(DEFAULT_DB_PATH)
    rag_enabled = bool(state.get("rag_enabled", _env_flag("RAG_ENABLED", "true")))
    rag_top_k = int(state.get("rag_top_k", os.getenv("RAG_TOP_K", "4")))
    init_db(sqlite_db_path)
    get_story_client().assert_ready()
    logger.info(
        "node=collect_requirements stage=end story_id=%s roles=%d max_retry=%s",
        story_id,
        len(roles),
        max_retry,
    )
    _emit_event(
        state,
        {
            "event": "node_log",
            "node": "collect_requirements",
            "message": "requirements collected and health check passed",
        },
    )

    return {
        **state,
        "story_id": story_id,
        "topic": topic,
        "style": style,
        "roles": roles,
        "retry_count": state.get("retry_count", 0),
        "max_retry": max_retry,
        "sqlite_db_path": sqlite_db_path,
        "rag_enabled": rag_enabled,
        "rag_top_k": rag_top_k,
    }


def load_story_framework_node(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=load_story_framework stage=start story_id=%s", state.get("story_id"))
    story_id, framework = load_story_framework(
        story_id=state.get("story_id", DEFAULT_STORY_ID),
        stories_dir=STORIES_DIR,
    )
    logger.info("node=load_story_framework stage=end resolved_story_id=%s", story_id)
    return {**state, "story_id": story_id, "story_framework": framework}


def load_roles(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=load_roles stage=start")
    roles = state.get("roles", [])
    assets = load_role_assets(ROLE_DIR, roles, memory_dir=MEMORY_DIR)
    db_path = state.get("sqlite_db_path", str(DEFAULT_DB_PATH))

    for role_id, role_asset in assets.items():
        upsert_role_asset(
            role_id=role_id,
            profile=role_asset.get("profile", ""),
            memory=role_asset.get("memory", ""),
            db_path=db_path,
        )

    logger.info("node=load_roles stage=end roles_loaded=%d", len(assets))

    return {**state, "role_assets": assets}


def index_role_memories_for_rag(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    if not state.get("rag_enabled", True):
        logger.info("node=index_role_memories_for_rag stage=skip rag_enabled=false")
        return {**state, "rag_indexed_docs": 0}

    logger.info("node=index_role_memories_for_rag stage=start")
    indexed = index_memory_directory(
        memory_dir=MEMORY_DIR,
        roles=state.get("roles", []),
    )
    logger.info("node=index_role_memories_for_rag stage=end indexed_docs=%d", indexed)
    _emit_event(
        state,
        {
            "event": "node_log",
            "node": "index_role_memories_for_rag",
            "message": f"indexed memory docs for rag: {indexed}",
        },
    )
    return {**state, "rag_indexed_docs": indexed}


def plan_global_story(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=plan_global_story stage=start")
    client = get_story_client()
    token_callback = state.get("event_callback") if callable(state.get("event_callback")) else None
    outline = client.plan_global_story(
        topic=state["topic"],
        style=state["style"],
        role_ids=state.get("roles", []),
        framework=state.get("story_framework", ""),
        token_callback=token_callback,
    )
    logger.info("node=plan_global_story stage=end outline_chars=%d", len(outline))

    return {**state, "global_outline": outline}


def retrieve_role_rag_contexts(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    if not state.get("rag_enabled", True):
        logger.info("node=retrieve_role_rag_contexts stage=skip rag_enabled=false")
        return {**state, "rag_role_contexts": {}}

    logger.info("node=retrieve_role_rag_contexts stage=start")
    story_id = state.get("story_id", DEFAULT_STORY_ID)
    top_k = int(state.get("rag_top_k", 4))
    role_scope = state.get("roles", [])
    contexts: dict[str, str] = {}

    for role_id in role_scope:
        role_asset = state.get("role_assets", {}).get(role_id, {"profile": "", "memory": ""})
        query_text = "\n".join(
            [
                f"story_id={story_id}",
                f"role_id={role_id}",
                f"topic={state.get('topic', '')}",
                f"style={state.get('style', '')}",
                "global_outline:",
                state.get("global_outline", ""),
                "role_profile:",
                role_asset.get("profile", ""),
            ]
        )
        contexts[role_id] = format_role_rag_context(
            story_id=story_id,
            target_role_id=role_id,
            role_scope=role_scope,
            query_text=query_text,
            top_k=top_k,
        )
        logger.info(
            "node=retrieve_role_rag_contexts role_id=%s chars=%d",
            role_id,
            len(contexts[role_id]),
        )

    logger.info("node=retrieve_role_rag_contexts stage=end roles=%d", len(contexts))
    return {**state, "rag_role_contexts": contexts}


def generate_role_views(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=generate_role_views stage=start")
    client = get_story_client()
    outline = state["global_outline"]
    style = state["style"]
    role_assets = state.get("role_assets", {})
    rag_contexts = state.get("rag_role_contexts", {})
    drafts: dict[str, str] = {}
    token_callback = state.get("event_callback") if callable(state.get("event_callback")) else None

    for role_id in state.get("roles", []):
        asset = role_assets.get(role_id, {"profile": "", "memory": ""})
        logger.info("node=generate_role_views role_id=%s stage=start", role_id)
        drafts[role_id] = client.generate_role_view(
            role_id=role_id,
            profile=asset["profile"],
            memory=asset["memory"],
            rag_context=rag_contexts.get(role_id, ""),
            outline=outline,
            style=style,
            token_callback=token_callback,
        )
        logger.info(
            "node=generate_role_views role_id=%s stage=end chars=%d",
            role_id,
            len(drafts[role_id]),
        )

    logger.info("node=generate_role_views stage=end roles=%d", len(drafts))

    return {**state, "role_view_drafts": drafts}


def integrate_perspectives(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=integrate_perspectives stage=start")
    client = get_story_client()
    role_drafts = state.get("role_view_drafts", {})
    token_callback = state.get("event_callback") if callable(state.get("event_callback")) else None
    integrated = client.integrate_perspectives(
        topic=state.get("topic", ""),
        style=state.get("style", ""),
        role_drafts=role_drafts,
        token_callback=token_callback,
    )
    logger.info("node=integrate_perspectives stage=end chars=%d", len(integrated))

    return {**state, "integrated_draft": integrated}


def quality_check(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=quality_check stage=start")
    client = get_story_client()
    token_callback = state.get("event_callback") if callable(state.get("event_callback")) else None
    report = client.quality_check(
        outline=state.get("global_outline", ""),
        integrated_story=state.get("integrated_draft", ""),
        role_ids=state.get("roles", []),
        token_callback=token_callback,
    )
    retry_count = state.get("retry_count", 0)
    if "FAIL" in report.upper():
        retry_count += 1
    logger.info(
        "node=quality_check stage=end status=%s retry_count=%s",
        "FAIL" if "FAIL" in report.upper() else "PASS",
        retry_count,
    )
    return {**state, "quality_report": report, "retry_count": retry_count}


def route_after_quality(state: StoryState) -> str:
    report = state.get("quality_report", "")
    retry_count = state.get("retry_count", 0)
    max_retry = state.get("max_retry", 1)
    if "FAIL" in report.upper() and retry_count <= max_retry:
        return "generate_role_views"
    return "finalize_output"


def finalize_output(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=finalize_output stage=start")
    final_story = state.get("integrated_draft", "")
    quality_report = state.get("quality_report", "")
    retry_count = state.get("retry_count", 0)
    if quality_report and "FAIL" in quality_report.upper():
        final_story = (
            "[Quality Check: FAIL]\n"
            "The integrated story may contain consistency issues after retry attempts.\n"
            f"retry_count={retry_count}\n\n"
            + final_story
        )

    run_id = insert_story_run(
        topic=state.get("topic", ""),
        style=state.get("style", ""),
        roles_json=json.dumps(state.get("roles", []), ensure_ascii=True),
        integrated_draft=state.get("integrated_draft", ""),
        final_story=final_story,
        db_path=state.get("sqlite_db_path", str(DEFAULT_DB_PATH)),
    )

    chapter_timestamp = state.get("chapter_timestamp") or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    memory_slice_paths: list[str] = []
    for role_id, role_story in state.get("role_view_drafts", {}).items():
        path = persist_generated_role_slice(
            memory_dir=MEMORY_DIR,
            role_id=role_id,
            story_id=state.get("story_id", DEFAULT_STORY_ID),
            run_id=run_id,
            chapter_timestamp=chapter_timestamp,
            topic=state.get("topic", ""),
            style=state.get("style", ""),
            content=role_story,
        )
        memory_slice_paths.append(str(path))

    rag_indexed_docs = state.get("rag_indexed_docs", 0)
    if state.get("rag_enabled", True):
        rag_indexed_docs = index_memory_directory(memory_dir=MEMORY_DIR, roles=state.get("roles", []))

    _emit_event(
        state,
        {
            "event": "node_log",
            "node": "finalize_output",
            "message": (
                f"saved chapter memories at {chapter_timestamp}, "
                f"files={len(memory_slice_paths)}, rag_indexed_docs={rag_indexed_docs}"
            ),
        },
    )
    logger.info("node=finalize_output stage=end run_id=%s", run_id)
    return {
        **state,
        "final_story": final_story,
        "run_id": run_id,
        "chapter_timestamp": chapter_timestamp,
        "memory_slice_paths": memory_slice_paths,
        "rag_indexed_docs": rag_indexed_docs,
    }


def build_graph():
    graph = StateGraph(StoryState)
    graph.add_node("collect_requirements", collect_requirements)
    graph.add_node("load_story_framework", load_story_framework_node)
    graph.add_node("load_roles", load_roles)
    graph.add_node("index_role_memories_for_rag", index_role_memories_for_rag)
    graph.add_node("plan_global_story", plan_global_story)
    graph.add_node("retrieve_role_rag_contexts", retrieve_role_rag_contexts)
    graph.add_node("generate_role_views", generate_role_views)
    graph.add_node("integrate_perspectives", integrate_perspectives)
    graph.add_node("quality_check", quality_check)
    graph.add_node("finalize_output", finalize_output)

    graph.add_edge(START, "collect_requirements")
    graph.add_edge("collect_requirements", "load_story_framework")
    graph.add_edge("load_story_framework", "load_roles")
    graph.add_edge("load_roles", "index_role_memories_for_rag")
    graph.add_edge("index_role_memories_for_rag", "plan_global_story")
    graph.add_edge("plan_global_story", "retrieve_role_rag_contexts")
    graph.add_edge("retrieve_role_rag_contexts", "generate_role_views")
    graph.add_edge("generate_role_views", "integrate_perspectives")
    graph.add_edge("integrate_perspectives", "quality_check")
    graph.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {
            "generate_role_views": "generate_role_views",
            "finalize_output": "finalize_output",
        },
    )
    graph.add_edge("finalize_output", END)

    return graph.compile()
