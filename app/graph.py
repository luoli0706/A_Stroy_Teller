import json
import logging
import os

from langgraph.graph import END, START, StateGraph

from app.llm_client import get_story_client
from app.role_memory import discover_roles, load_role_assets
from app.sqlite_store import DEFAULT_DB_PATH, init_db, insert_story_run, upsert_role_asset
from app.state import StoryState
from app.story_framework import DEFAULT_STORY_ID, load_story_framework


ROLE_DIR = "role"
MEMORY_DIR = "memory"
STORIES_DIR = "stories"


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


def generate_role_views(state: StoryState) -> StoryState:
    logger = _get_logger(state)
    logger.info("node=generate_role_views stage=start")
    client = get_story_client()
    outline = state["global_outline"]
    style = state["style"]
    role_assets = state.get("role_assets", {})
    drafts: dict[str, str] = {}
    token_callback = state.get("event_callback") if callable(state.get("event_callback")) else None

    for role_id in state.get("roles", []):
        asset = role_assets.get(role_id, {"profile": "", "memory": ""})
        logger.info("node=generate_role_views role_id=%s stage=start", role_id)
        drafts[role_id] = client.generate_role_view(
            role_id=role_id,
            profile=asset["profile"],
            memory=asset["memory"],
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
    logger.info("node=finalize_output stage=end run_id=%s", run_id)
    return {**state, "final_story": final_story, "run_id": run_id}


def build_graph():
    graph = StateGraph(StoryState)
    graph.add_node("collect_requirements", collect_requirements)
    graph.add_node("load_story_framework", load_story_framework_node)
    graph.add_node("load_roles", load_roles)
    graph.add_node("plan_global_story", plan_global_story)
    graph.add_node("generate_role_views", generate_role_views)
    graph.add_node("integrate_perspectives", integrate_perspectives)
    graph.add_node("quality_check", quality_check)
    graph.add_node("finalize_output", finalize_output)

    graph.add_edge(START, "collect_requirements")
    graph.add_edge("collect_requirements", "load_story_framework")
    graph.add_edge("load_story_framework", "load_roles")
    graph.add_edge("load_roles", "plan_global_story")
    graph.add_edge("plan_global_story", "generate_role_views")
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
