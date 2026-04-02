# A Story Teller API / 接口说明

## 1. 当前 API 形态 / Current API Shape

- 中文：当前项目以 Python 模块 API 为主（非 HTTP 服务）。
- English: The project is currently module-first (Python APIs), not an HTTP service yet.

## 2. Graph API (`app/graph.py`)

### 2.1 `build_graph()`

- 中文：构建并返回编译后的 LangGraph。
- English: Builds and returns the compiled LangGraph.

### 2.2 节点链路 / Node Chain

- `collect_requirements`
- `load_story_framework`
- `load_roles`
- `index_role_memories_for_rag`
- `plan_global_story`
- `retrieve_role_rag_contexts`
- `generate_role_views`
- `integrate_perspectives`
- `quality_check`
- `finalize_output`

重试回路 / Retry route:

- 中文：`quality_check` 为 FAIL 且未超过最大重试时回到 `generate_role_views`。
- English: On FAIL and within retry limit, routing goes back to `generate_role_views`.

## 3. LLM API (`app/llm_client.py`)

### 3.1 `get_story_client()`

- 中文：返回缓存的 `OllamaStoryClient` 单例。
- English: Returns cached singleton `OllamaStoryClient`.

### 3.2 健康检查 / Health

- `health_check()`：检查 Ollama 可达性及规划/角色/整合/质检/embedding 模型可用性。
- `assert_ready()`：启动时强校验，失败抛异常。

### 3.3 生成方法 / Generation Methods

- `plan_global_story(topic, style, role_ids, framework)`
- `generate_role_view(role_id, profile, memory, rag_context, outline, style)`
- `integrate_perspectives(topic, style, role_drafts)`
- `quality_check(outline, integrated_story, role_ids)`

## 4. Role API (`app/role_memory.py`)

- `discover_roles(base_dir)`：发现角色目录。
- `load_role_assets(base_dir, roles, memory_dir="memory")`：加载 profile 与聚合 memory。
- `add_role_profile(role_id, profile_text, role_dir="role")`：新增/覆盖设定。
- `delete_role_profile(role_id, role_dir="role")`：删除设定。
- `add_role_memory_slice(role_id, story_id, memory_text, memory_dir="memory")`：新增/覆盖记忆切片。
- `delete_role_memory_slice(role_id, story_id, memory_dir="memory")`：删除单条切片。
- `delete_all_role_memories(role_id, memory_dir="memory", role_dir="role")`：删除全部切片。

## 5. SQLite API (`app/sqlite_store.py`)

- `init_db(db_path=DEFAULT_DB_PATH)`：初始化数据库。
- `upsert_role_asset(role_id, profile, memory, db_path=DEFAULT_DB_PATH)`：写入角色资产快照。
- `insert_story_run(topic, style, roles_json, integrated_draft, final_story, db_path=DEFAULT_DB_PATH)`：写入运行记录并返回 `run_id`。

## 6. 环境变量合约 / Environment Contract

` .env ` 为本地配置，` .env.example ` 为模板。

核心键：

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL_PLANNER=qwen3.5:9b`
- `OLLAMA_MODEL_ROLE=qwen3.5:9b`
- `OLLAMA_MODEL_INTEGRATOR=qwen3.5:9b`
- `OLLAMA_MODEL_QUALITY=qwen3.5:9b`
- `OLLAMA_MODEL_EMBEDDING=nomic-embed-text-v2-moe`
- `OLLAMA_TEMPERATURE=0.7`
- `RAG_ENABLED=true`
- `RAG_TOP_K=4`
- `RAG_CHROMA_DIR=.data/rag_chroma`
- `RAG_COLLECTION_NAME=story_memory_slices`

## 7. 运行接口 / Runtime Entry

主入口 / Main entry:

```bash
python -m app.main
```

流式模式 / Streaming mode:

```bash
python -m app.main --stream
```

RAG 示例 / RAG example:

```bash
python -m app.main --story-id future_academy_city --topic "campus anomaly at night" --style cinematic --roles "Reshaely,VanlyShan,SolinXuan" --rag-enabled true --rag-top-k 4
```

### 7.1 Runtime API (`app/runtime.py`)

- `build_input_state(...)`：支持 `rag_enabled` 与 `rag_top_k`。
- `run_story(state)`：非流式执行。
- `stream_story_events(state)`：流式事件输出（node + token）。

状态新增字段 / New state fields:

- `rag_enabled`
- `rag_top_k`
- `rag_indexed_docs`
- `rag_role_contexts`
- `chapter_timestamp`
- `memory_slice_paths`

### 7.2 日志与监控 / Logs & Observability

- 控制台结构化日志 / Structured console logs
- 文件日志 `logs/run_<timestamp>.log`
- 实现模块 `app/observability.py`

### 7.3 流式事件类型 / Event Types

- `token`: LLM token chunk event
- `node_update`: LangGraph node update event
- `done`: stream completed
- `error`: stream failed

## 8. 脚本 / Scripts

- `scripts/test_role_ops.py`：角色资产接口脚本 / role-asset script

## 9. CLI 工具 / CLI Tools

### 9.1 Role CLI (`tools/role_cli.py`)

```bash
python tools/role_cli.py list-roles
python tools/role_cli.py add-profile Reshaely --file role/Reshaely/profile.md
python tools/role_cli.py delete-profile alice
python tools/role_cli.py add-memory SolinXuan case_001 --text "- clue A\n- clue B"
python tools/role_cli.py delete-memory SolinXuan case_001
python tools/role_cli.py delete-all-memory bob
```

### 9.2 Embedding CLI (`tools/embedding_cli.py`)

```bash
python tools/embedding_cli.py index --roles "Reshaely,VanlyShan,SolinXuan"
python tools/embedding_cli.py query --story-id future_academy_city --target-role Reshaely --roles "Reshaely,VanlyShan,SolinXuan" --query "chapter timeline" --top-k 4
```

## 10. RAG API

### 10.1 `app.rag.ollama_embedding`

- `OllamaEmbeddingClient.embed_texts(texts)`：调用 Ollama embedding 接口（`/api/embed`，兼容 `/api/embeddings`）。

### 10.2 `app.rag.chroma_memory`

- `index_memory_directory(...)`：索引记忆切片到 Chroma。
- `format_role_rag_context(...)`：检索并格式化角色 RAG 上下文。
- `persist_generated_role_slice(...)`：写入章节时间戳记忆切片。

### 10.3 章节时间戳机制 / Chapter Timestamp Mechanism

- 格式 / Format: `%Y%m%dT%H%M%SZ` (UTC)
- 文件名 / Filename: `<story_id>__chapter_<timestamp>_run<run_id>.md`
- Header 字段 / Header fields:
  - `Story ID`
  - `Role ID`
  - `Chapter Timestamp`
  - `Run ID`
  - `Topic`
  - `Style`

## 11. 规划中的 HTTP API / Planned HTTP APIs

后续建议增加 FastAPI：

- `POST /stories/generate`
- `GET /stories/runs/{run_id}`
- `GET /roles`
- `POST /roles/{role_id}/memory`

English: Future service mode can expose the same capabilities via FastAPI endpoints.

## 12. Flet UI (`UI/flet_app.py`)

- 中文：支持故事/角色/设置三页面、流式输出、框架与角色加载编辑、单多角色生成、中英切换与导出。
- English: Supports Story/Roles/Settings routes, streaming output, framework/role load-edit flows, single/multi-role generation, bilingual UI, and export.
