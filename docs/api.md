# A Story Teller API 说明 (v0.2.5)

## 1. 后端运行时 (app.runtime)

### `stream_story_events_async(state: StoryState, thread_id: str) -> AsyncIterator`
**核心流式接口**。采用 `astream_events(v2)` 捕获节点生命周期。
- **返回事件**：`node_start`, `token`, `node_update`, `error`, `done`。
- **持久化**：自动通过 `AsyncSqliteSaver` 关联 `thread_id`。

### `get_thread_history_async(thread_id: str) -> List[Dict]`
回溯指定会话的所有历史状态。用于 UI 层的 Checkpoint 可视化。

## 2. 推理客户端 (app.llm_client)

### `adapt_role_to_framework_async(...) -> str (JSON)`
让演员生成符合剧本的特定身份。
### `generate_relationships_async(...) -> str`
根据演员阵容生成社交关系矩阵。

## 3. 存储与检索 (app.rag)

### `index_memory_directory(roles: list[str]) -> int`
**增量索引接口**。使用 SHA-256 哈希比对，仅同步变更文件。
