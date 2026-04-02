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
    
    # 构造 Pydantic 模型
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
    """递归处理 Pydantic 模型或其他非 JSON 序列化对象。"""
    if hasattr(value, "dict"):
        return _sanitize_for_json(value.dict())
    if isinstance(value, dict):
        return {str(k): _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(i) for i in value]
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return str(value)


async def run_story_async(state: StoryState) -> Dict[str, Any]:
    graph = build_graph()
    # 转换为 dict 传给 LangGraph，因为它内部处理 Pydantic 可能有版本兼容问题
    result = await graph.ainvoke(state.dict())
    return _sanitize_for_json(result)


async def stream_story_events_async(state: StoryState) -> AsyncIterator[dict]:
    """异步流式产生事件。"""
    graph = build_graph()
    
    try:
        # 传入模型或字典
        async for update in graph.astream(state.dict(), stream_mode="updates"):
            for node_name, node_update in update.items():
                yield {
                    "event": "node_update",
                    "node": node_name,
                    "data": _sanitize_for_json(node_update),
                }
        yield {"event": "done"}
    except Exception as exc:
        yield {"event": "error", "message": str(exc)}
