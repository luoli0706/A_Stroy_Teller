import json

from langgraph.graph import END, START, StateGraph

from app.role_memory import discover_roles, load_role_assets
from app.sqlite_store import DEFAULT_DB_PATH, init_db, insert_story_run, upsert_role_asset
from app.state import StoryState


ROLE_DIR = "role"


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
    assets = load_role_assets(ROLE_DIR, roles)
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
    topic = state["topic"]
    outline = (
        f"Act 1: Introduce tension around {topic}. "
        f"Act 2: Reveal hidden motives and conflicting interpretations. "
        f"Act 3: Resolve conflict and close emotional arcs."
    )

    return {**state, "global_outline": outline}


def generate_role_views(state: StoryState) -> StoryState:
    outline = state["global_outline"]
    style = state["style"]
    role_assets = state.get("role_assets", {})
    drafts: dict[str, str] = {}

    for role_id in state.get("roles", []):
        asset = role_assets.get(role_id, {"profile": "", "memory": ""})
        drafts[role_id] = (
            f"[{role_id.upper()} VIEW]\n"
            f"Style target: {style}.\n"
            f"Outline anchor: {outline}\n\n"
            f"Role profile:\n{asset['profile']}\n\n"
            f"Role memory:\n{asset['memory']}\n\n"
            f"Narration:\n"
            f"From {role_id}'s perspective, the same event looks different because of personal goals and memory bias."
        )

    return {**state, "role_view_drafts": drafts}


def integrate_perspectives(state: StoryState) -> StoryState:
    role_drafts = state.get("role_view_drafts", {})
    merged_sections = [f"## {role_id}\n{text}" for role_id, text in role_drafts.items()]
    integrated = "# Integrated Story\n\n" + "\n\n".join(merged_sections)

    return {**state, "integrated_draft": integrated}


def finalize_output(state: StoryState) -> StoryState:
    final_story = state.get("integrated_draft", "")
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
    graph.add_node("finalize_output", finalize_output)

    graph.add_edge(START, "collect_requirements")
    graph.add_edge("collect_requirements", "load_roles")
    graph.add_edge("load_roles", "plan_global_story")
    graph.add_edge("plan_global_story", "generate_role_views")
    graph.add_edge("generate_role_views", "integrate_perspectives")
    graph.add_edge("integrate_perspectives", "finalize_output")
    graph.add_edge("finalize_output", END)

    return graph.compile()
