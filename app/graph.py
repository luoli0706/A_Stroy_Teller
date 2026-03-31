import json

from langgraph.graph import END, START, StateGraph

from app.llm_client import get_story_client
from app.role_memory import discover_roles, load_role_assets
from app.sqlite_store import DEFAULT_DB_PATH, init_db, insert_story_run, upsert_role_asset
from app.state import StoryState


ROLE_DIR = "role"
MEMORY_DIR = "memory"


def collect_requirements(state: StoryState) -> StoryState:
    topic = state.get("topic", "an unexpected friendship")
    style = state.get("style", "warm")
    roles = state.get("roles") or discover_roles(ROLE_DIR)
    sqlite_db_path = state.get("sqlite_db_path") or str(DEFAULT_DB_PATH)
    init_db(sqlite_db_path)

    return {
        **state,
        "topic": topic,
        "style": style,
        "roles": roles,
        "sqlite_db_path": sqlite_db_path,
    }


def load_roles(state: StoryState) -> StoryState:
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

    return {**state, "role_assets": assets}


def plan_global_story(state: StoryState) -> StoryState:
    client = get_story_client()
    outline = client.plan_global_story(
        topic=state["topic"],
        style=state["style"],
        role_ids=state.get("roles", []),
    )

    return {**state, "global_outline": outline}


def generate_role_views(state: StoryState) -> StoryState:
    client = get_story_client()
    outline = state["global_outline"]
    style = state["style"]
    role_assets = state.get("role_assets", {})
    drafts: dict[str, str] = {}

    for role_id in state.get("roles", []):
        asset = role_assets.get(role_id, {"profile": "", "memory": ""})
        drafts[role_id] = client.generate_role_view(
            role_id=role_id,
            profile=asset["profile"],
            memory=asset["memory"],
            outline=outline,
            style=style,
        )

    return {**state, "role_view_drafts": drafts}


def integrate_perspectives(state: StoryState) -> StoryState:
    client = get_story_client()
    role_drafts = state.get("role_view_drafts", {})
    integrated = client.integrate_perspectives(
        topic=state.get("topic", ""),
        style=state.get("style", ""),
        role_drafts=role_drafts,
    )

    return {**state, "integrated_draft": integrated}


def quality_check(state: StoryState) -> StoryState:
    client = get_story_client()
    report = client.quality_check(
        outline=state.get("global_outline", ""),
        integrated_story=state.get("integrated_draft", ""),
        role_ids=state.get("roles", []),
    )
    return {**state, "quality_report": report}


def finalize_output(state: StoryState) -> StoryState:
    final_story = state.get("integrated_draft", "")
    quality_report = state.get("quality_report", "")
    if quality_report and "FAIL" in quality_report.upper():
        final_story = (
            "[Quality Check: FAIL]\n"
            "The integrated story may contain consistency issues.\n\n"
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
    return {**state, "final_story": final_story, "run_id": run_id}


def build_graph():
    graph = StateGraph(StoryState)
    graph.add_node("collect_requirements", collect_requirements)
    graph.add_node("load_roles", load_roles)
    graph.add_node("plan_global_story", plan_global_story)
    graph.add_node("generate_role_views", generate_role_views)
    graph.add_node("integrate_perspectives", integrate_perspectives)
    graph.add_node("quality_check", quality_check)
    graph.add_node("finalize_output", finalize_output)

    graph.add_edge(START, "collect_requirements")
    graph.add_edge("collect_requirements", "load_roles")
    graph.add_edge("load_roles", "plan_global_story")
    graph.add_edge("plan_global_story", "generate_role_views")
    graph.add_edge("generate_role_views", "integrate_perspectives")
    graph.add_edge("integrate_perspectives", "quality_check")
    graph.add_edge("quality_check", "finalize_output")
    graph.add_edge("finalize_output", END)

    return graph.compile()
