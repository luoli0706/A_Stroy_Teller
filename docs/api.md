# A Story Teller API 说明 (Alpha 0.1)

## 1. 核心模型接口 (app.llm_client)

### `get_story_client() -> OllamaStoryClient`
获取全局共享的 Ollama 客户端实例。

#### `OllamaStoryClient` 主要异步方法：
- **`plan_global_story_async(...) -> str`**: 生成故事大纲。
- **`generate_role_view_async(...) -> str`**: 并发调用，生成角色视角叙事。
- **`integrate_perspectives_async(...) -> str`**: 融合多角色叙事产出最终成果。
- **`quality_check_async(...) -> str`**: 质检节点异步评估。

## 2. RAG 与向量存储接口 (app.rag.chroma_memory)

### `index_memory_directory(roles: list[str]) -> int`
**[Alpha 0.1 优化]**：同步构建/更新指定角色的向量索引。

### `format_role_rag_context_async(...) -> str`
**[Efficiency Boost]**：使用原生 `query` 接口异步检索。支持 `where={"story_id": ...}` 元数据过滤，显著提升召回精度。

## 3. 运行时接口 (app.runtime)

### `build_input_state(...) -> StoryState`
初始化 Graph 输入状态，配置日志记录。

### `stream_story_events_async(state: StoryState) -> AsyncIterator[dict]`
**[Core Bridge]**：核心流式接口。返回异步迭代器，实时推送 `token`（流式输出）与 `node_update`（节点状态）事件。

## 4. 角色与记忆管理 (app.role_memory)

### `discover_roles() -> list[str]`
从配置的 `ROLE_DIR` 发现角色文件夹。

### `persist_generated_role_slice(...) -> Path`
持久化生成后的角色视角，按照 `<story_id>__chapter_<timestamp>_run<run_id>.md` 规则存储，支持章节化管理。
