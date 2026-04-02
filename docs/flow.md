# A Story Teller Flow / 流程说明

## 1. 流程总览 / Overview

### 中文

当前系统采用 LangGraph 编排，围绕角色中心多视角叙事生成。

主流程节点：

1. collect_requirements
2. load_story_framework
3. load_roles
4. index_role_memories_for_rag
5. plan_global_story
6. retrieve_role_rag_contexts
7. generate_role_views
8. integrate_perspectives
9. quality_check
10. finalize_output

图路径：

`START -> collect_requirements -> load_story_framework -> load_roles -> index_role_memories_for_rag -> plan_global_story -> retrieve_role_rag_contexts -> generate_role_views -> integrate_perspectives -> quality_check -> finalize_output -> END`

流式能力：

- 使用 `python -m app.main --stream` 启用。
- 以 JSON 行输出节点事件，并附带 token 事件供 UI 实时渲染。

监控能力：

- 控制台结构化日志。
- 文件日志 `logs/run_<timestamp>.log`。
- 记录 pid、节点阶段、重试次数、run_id。

### English

The system is orchestrated by LangGraph and generates stories with role-centered multi-perspective narration.

Main pipeline nodes:

1. collect_requirements
2. load_story_framework
3. load_roles
4. index_role_memories_for_rag
5. plan_global_story
6. retrieve_role_rag_contexts
7. generate_role_views
8. integrate_perspectives
9. quality_check
10. finalize_output

Graph path:

`START -> collect_requirements -> load_story_framework -> load_roles -> index_role_memories_for_rag -> plan_global_story -> retrieve_role_rag_contexts -> generate_role_views -> integrate_perspectives -> quality_check -> finalize_output -> END`

Streaming:

- Enable with `python -m app.main --stream`.
- Node events are emitted as JSON lines, plus token events for realtime UI updates.

Observability:

- Structured console logs.
- File logs at `logs/run_<timestamp>.log`.
- Captures pid, node stage, retry count, and run_id.

## 2. 节点职责 / Node Responsibilities

### 2.1 collect_requirements

- 中文：读取输入（topic/style/roles），自动发现角色，初始化 SQLite，并做 Ollama 健康检查。
- English: Reads inputs (topic/style/roles), auto-discovers roles, initializes SQLite, and performs Ollama health checks.

### 2.2 load_story_framework

- 中文：从 `stories/<story_id>/framework.md` 加载框架，未命中回退 `stories/default/framework.md`。
- English: Loads `stories/<story_id>/framework.md`, and falls back to `stories/default/framework.md`.

### 2.3 load_roles

- 中文：读取 `profile.md` 与记忆切片目录，聚合后 upsert 到 SQLite `role_assets`。
- English: Loads role profiles and memory slices, then upserts aggregated assets into SQLite `role_assets`.

### 2.4 index_role_memories_for_rag

- 中文：将 `memory/<role_id>/*.md` 嵌入并写入 Chroma，`RAG_ENABLED=false` 时可关闭。
- English: Embeds `memory/<role_id>/*.md` slices into Chroma; can be disabled via `RAG_ENABLED=false`.

### 2.5 plan_global_story

- 中文：在故事框架约束下生成三幕式主线与共享事实。
- English: Generates a global outline and shared facts under framework constraints.

### 2.6 retrieve_role_rag_contexts

- 中文：按角色检索同框架切片，优先同 `story_id`，结果含 `source_role` / `slice_id` / `chapter_timestamp`。
- English: Retrieves role-scoped context with same-story preference; results include `source_role`, `slice_id`, and `chapter_timestamp`.

### 2.7 generate_role_views

- 中文：按角色分别生成视角稿，输入 profile + memory + RAG context + global_outline。
- English: Generates per-role drafts using profile, memory, RAG context, and global outline.

### 2.8 integrate_perspectives

- 中文：整合多角色视角为统一正文。
- English: Integrates all role drafts into one coherent story.

### 2.9 quality_check

- 中文：输出 PASS/FAIL 报告；当 FAIL 且 `retry_count <= max_retry` 时回到 `generate_role_views`。
- English: Produces PASS/FAIL quality report; on FAIL and `retry_count <= max_retry`, routes back to `generate_role_views`.

### 2.10 finalize_output

- 中文：输出 final_story，写入 SQLite `story_runs`，并为每个角色写入章节记忆切片，随后刷新 RAG 索引。
- English: Finalizes `final_story`, persists run data to SQLite `story_runs`, writes chapter memory slices per role, then refreshes RAG index.

切片文件格式 / Slice filename format:

`memory/<role_id>/<story_id>__chapter_<timestamp>_run<run_id>.md`

## 3. 文件与数据布局 / File and Data Layout

### 3.1 角色目录 / Role Directory

```text
role/
  Reshaely/profile.md
  VanlyShan/profile.md
  SolinXuan/profile.md
```

### 3.2 记忆目录 / Memory Directory

```text
memory/
  <role_id>/*.md
```

### 3.3 SQLite

- 中文：默认路径 `.data/story_teller.db`，核心表 `role_assets` 与 `story_runs`。
- English: Default DB path is `.data/story_teller.db`, with core tables `role_assets` and `story_runs`.

### 3.4 环境配置 / Environment

- `.env`：本地配置（不跟踪） / Local config (git-ignored)
- `.env.example`：模板（跟踪） / Template (tracked)
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL_*=qwen3.5:9b`
- `OLLAMA_MODEL_EMBEDDING=nomic-embed-text-v2-moe`
- `RAG_ENABLED=true`
- `RAG_TOP_K=4`
- `RAG_CHROMA_DIR=.data/rag_chroma`
- `RAG_COLLECTION_NAME=story_memory_slices`

### 3.5 故事框架目录 / Story Framework Directory

```text
stories/
  default/framework.md
  urban_detective/framework.md
  future_academy_city/framework.md
```

### 3.6 RAG 目录 / RAG Directory

```text
app/rag/
  chroma_memory.py
  ollama_embedding.py
RAG/README.md
tools/embedding_cli.py
```

## 4. 后续建议 / Next Improvements

1. 中文：在 quality_check 后增加局部重写回路。 / English: Add local rewrite routes after quality_check.
2. 中文：增加章节时间衰减检索策略。 / English: Add chapter-time decay retrieval strategy.
3. 中文：增加角色并行限流策略。 / English: Add parallel generation throttling.

## 5. 脚本组织 / Script Organization

- `scripts/test_role_ops.py`：角色资产接口测试 / Role asset API test script
- `tools/role_cli.py`：角色管理 CLI / Role management CLI
- `tools/embedding_cli.py`：RAG 索引与检索 CLI / RAG indexing and retrieval CLI
