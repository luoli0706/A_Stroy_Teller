from collections.abc import AsyncIterator
import asyncio
from typing import Any, Dict, List, Optional

from app.graph import build_graph
from app.observability import create_run_logger
from app.state import StoryState


def build_input_state(
    story_id: str,
    topic: str,
    style: str,
    roles: List[str],
    max_retry: int,
    rag_enabled: Optional[bool] = None,
    rag_top_k: Optional[int] = None,
) -> StoryState:
    logger, log_file_path = create_run_logger()
    
    state = StoryState(
        logger_name=logger.name,
        log_file_path=log_file_path,
        story_id=story_id,
        topic=topic,
        style=style,
        roles=roles,
        max_retry=max_retry
    )

    if rag_enabled is not None:
        state.rag_enabled = bool(rag_enabled)
    if rag_top_k is not None:
        state.rag_top_k = int(rag_top_k)

    return state


def _sanitize_for_json(value: Any) -> Any:
    if hasattr(value, "dict"):
        return _sanitize_for_json(value.dict())
    if isinstance(value, dict):
        return {str(k): _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(i) for i in value]
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return str(value)


async def run_story_async(state: StoryState, thread_id: str = "default_thread") -> Dict[str, Any]:
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(state.model_dump(), config=config)
    return _sanitize_for_json(result)


async def stream_story_events_async(state: StoryState, thread_id: str = "default_thread") -> AsyncIterator[dict]:
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        async for update in graph.astream(state.model_dump(), config=config, stream_mode="updates"):
            for node_name, node_update in update.items():
                yield {
                    "event": "node_update",
                    "node": node_name,
                    "data": _sanitize_for_json(node_update),
                }
        yield {"event": "done"}
    except Exception as exc:
        yield {"event": "error", "message": str(exc)}


async def get_thread_history_async(thread_id: str) -> List[Dict[str, Any]]:
    """[v0.2.5] 获取指定线程的持久化历史快照。"""
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    history = []
    # get_state_history 返回一个迭代器，列出所有历史状态
    # 注意：根据 LangGraph 版本不同，此方法可能是同步或异步，
    # 这里我们使用通用的同步迭代器包装（如果是同步的）。
    try:
        for state in graph.get_state_history(config):
            history.append({
                "values": _sanitize_for_json(state.values),
                "next": state.next,
                "created_at": state.created_at if hasattr(state, "created_at") else None,
                "metadata": state.metadata,
                "config": state.config
            })
    except Exception as e:
        print(f"Error fetching history: {e}")
        
    return history
