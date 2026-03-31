from collections.abc import Iterator
from queue import Empty, Queue
import threading
from typing import Any

from app.graph import build_graph
from app.observability import create_run_logger
from app.state import StoryState


def build_input_state(
    story_id: str,
    topic: str,
    style: str,
    roles: list[str],
    max_retry: int,
) -> StoryState:
    logger, log_file_path = create_run_logger()
    logger.info("runtime=start story_id=%s topic=%s roles=%s", story_id, topic, ",".join(roles))

    return {
        "logger_name": logger.name,
        "log_file_path": log_file_path,
        "story_id": story_id,
        "topic": topic,
        "style": style,
        "roles": roles,
        "max_retry": max_retry,
    }


def _sanitize_for_json(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _sanitize_for_json(val)
            for key, val in value.items()
            if key != "event_callback"
        }
    if isinstance(value, list):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_json(item) for item in value]
    return str(value)


def run_story(state: StoryState) -> StoryState:
    graph = build_graph()
    result = graph.invoke(state)
    return {
        **result,
        "log_file_path": state.get("log_file_path", result.get("log_file_path", "")),
    }


def stream_story_events(state: StoryState) -> Iterator[dict[str, Any]]:
    queue: Queue[dict[str, Any]] = Queue()
    graph = build_graph()

    def event_callback(event: dict[str, Any]) -> None:
        queue.put(event)

    runtime_state = {**state, "event_callback": event_callback}

    def worker() -> None:
        try:
            for update in graph.stream(runtime_state, stream_mode="updates"):
                for node_name, node_update in update.items():
                    keys = sorted(node_update.keys())
                    queue.put(
                        {
                            "event": "node_update",
                            "node": node_name,
                            "keys": keys,
                            "data": _sanitize_for_json(node_update),
                        }
                    )
            queue.put({"event": "done"})
        except Exception as exc:
            queue.put({"event": "error", "message": str(exc)})
        finally:
            queue.put({"event": "_end"})

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while True:
        try:
            event = queue.get(timeout=0.2)
        except Empty:
            continue

        if event.get("event") == "_end":
            break
        yield event
