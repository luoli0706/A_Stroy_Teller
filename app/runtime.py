from collections.abc import AsyncIterator
import asyncio
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
    rag_enabled: bool | None = None,
    rag_top_k: int | None = None,
) -> StoryState:
    logger, log_file_path = create_run_logger()
    logger.info("runtime=start story_id=%s topic=%s roles=%s", story_id, topic, ",".join(roles))

    state: StoryState = {
        "logger_name": logger.name,
        "log_file_path": log_file_path,
        "story_id": story_id,
        "topic": topic,
        "style": style,
        "roles": roles,
        "max_retry": max_retry,
    }

    if rag_enabled is not None:
        state["rag_enabled"] = bool(rag_enabled)
    if rag_top_k is not None:
        state["rag_top_k"] = int(rag_top_k)

    return state


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
    return str(value)


async def run_story_async(state: StoryState) -> StoryState:
    graph = build_graph()
    result = await graph.ainvoke(state)
    return {
        **result,
        "log_file_path": state.get("log_file_path", result.get("log_file_path", "")),
    }


async def stream_story_events_async(state: StoryState) -> AsyncIterator[dict[str, Any]]:
    """异步流式产生事件。"""
    graph = build_graph()
    
    # 注入异步回调
    # 注意：LangGraph 的 stream_mode="updates" 会返回节点的增量更新
    try:
        async for update in graph.astream(state, stream_mode="updates"):
            for node_name, node_update in update.items():
                keys = sorted(node_update.keys())
                yield {
                    "event": "node_update",
                    "node": node_name,
                    "keys": keys,
                    "data": _sanitize_for_json(node_update),
                }
        yield {"event": "done"}
    except Exception as exc:
        yield {"event": "error", "message": str(exc)}
