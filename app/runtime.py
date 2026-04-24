from collections.abc import AsyncIterator
import asyncio
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.graph import build_graph
from app.observability import create_run_logger, log_event
from app.state import StoryState
from app.config import SQLITE_DB_PATH


def build_input_state(
    story_id: str,
    topic: str,
    style: str,
    roles: List[str],
    max_retry: int,
    rag_enabled: Optional[bool] = None,
    rag_top_k: Optional[int] = None,
) -> StoryState:
    # 创建具备落盘能力的 logger
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
        
    log_event(logger.name, f"Initialized input state for thread recovery. Log: {log_file_path}")
    return state


def _sanitize_for_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _sanitize_for_json(value.model_dump())
    if isinstance(value, dict):
        return {str(k): _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(i) for i in value]
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return str(value)


async def run_story_async(state: StoryState, thread_id: str = "default_thread") -> Dict[str, Any]:
    """异步运行故事生成。"""
    async with AsyncSqliteSaver.from_conn_string(str(SQLITE_DB_PATH)) as saver:
        graph = build_graph(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        result = await graph.ainvoke(state.model_dump(), config=config)
        return _sanitize_for_json(result)


import queue
import threading

def run_story(state: StoryState, thread_id: str = "default_thread") -> Dict[str, Any]:
    """同步封装运行故事。"""
    return asyncio.run(run_story_async(state, thread_id))


def stream_story_events(state: StoryState, thread_id: str = "default_thread"):
    """同步封装流式事件，支持实时消费。"""
    q = queue.Queue()

    def run_async_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _consume():
            try:
                async for event in stream_story_events_async(state, thread_id):
                    q.put(event)
            finally:
                q.put(None) # Sentinel to end iteration
            
        loop.run_until_complete(_consume())
        loop.close()

    # 在后台线程运行异步事件循环
    threading.Thread(target=run_async_loop, daemon=True).start()
    
    while True:
        event = q.get()
        if event is None:
            break
        yield event


async def stream_story_events_async(state: StoryState, thread_id: str = "default_thread") -> AsyncIterator[dict]:
    """
    [v0.2.5 优化版] 使用 astream_events 捕获全链路事件。
    """
    async with AsyncSqliteSaver.from_conn_string(str(SQLITE_DB_PATH)) as saver:
        graph = build_graph(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        
        log_event(state.logger_name, f"Starting stream for thread: {thread_id}")
        
        try:
            async for event in graph.astream_events(state.model_dump(), config=config, version="v2"):
                kind = event.get("event")
                
                if kind == "on_chain_update":
                    output = event.get("data", {}).get("output", {})
                    for node_name, node_update in output.items():
                        yield {
                            "event": "node_update",
                            "node": node_name,
                            "data": _sanitize_for_json(node_update),
                        }
                
                elif kind == "on_chat_model_stream":
                    content = event.get("data", {}).get("chunk", {}).content
                    if content:
                        yield {
                            "event": "token",
                            "text": content,
                            "node": event.get("metadata", {}).get("langgraph_node", "unknown")
                        }
                
                elif kind == "on_chain_start":
                    node_name = event.get("metadata", {}).get("langgraph_node")
                    if node_name:
                        yield {
                            "event": "node_start",
                            "node": node_name
                        }

            yield {"event": "done"}
        except Exception as exc:
            log_event(state.logger_name, f"Stream Critical Error: {str(exc)}", level=40)
            yield {"event": "error", "message": str(exc)}


async def get_thread_history_async(thread_id: str) -> List[Dict[str, Any]]:
    async with AsyncSqliteSaver.from_conn_string(str(SQLITE_DB_PATH)) as saver:
        graph = build_graph(checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}}
        history = []
        try:
            async for state in graph.get_state_history(config):
                history.append({
                    "values": _sanitize_for_json(state.values),
                    "next": state.next,
                    "created_at": getattr(state, "created_at", None),
                    "metadata": _sanitize_for_json(state.metadata),
                    "config": _sanitize_for_json(state.config)
                })
        except Exception as e:
            print(f"Error fetching history: {e}")
        return history
