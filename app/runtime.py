from collections.abc import Iterator
from typing import Any

from app.graph import build_graph
from app.state import StoryState


def build_input_state(
    story_id: str,
    topic: str,
    style: str,
    roles: list[str],
    max_retry: int,
) -> StoryState:
    return {
        "story_id": story_id,
        "topic": topic,
        "style": style,
        "roles": roles,
        "max_retry": max_retry,
    }


def run_story(state: StoryState) -> StoryState:
    graph = build_graph()
    result = graph.invoke(state)
    return result


def stream_story_events(state: StoryState) -> Iterator[dict[str, Any]]:
    graph = build_graph()
    for update in graph.stream(state, stream_mode="updates"):
        for node_name, node_update in update.items():
            keys = sorted(node_update.keys())
            yield {
                "event": "node_update",
                "node": node_name,
                "keys": keys,
                "data": node_update,
            }
