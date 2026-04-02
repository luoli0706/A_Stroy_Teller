# RAG Workspace / RAG 工作区

## 中文

该目录用于记录本项目的 RAG（检索增强生成）能力与使用方式。

### 运行时存储

- 向量库路径由 `RAG_CHROMA_DIR` 配置。
- 默认路径：`.data/rag_chroma/`（不纳入 git）。
- 向量集合名由 `RAG_COLLECTION_NAME` 配置（默认 `story_memory_slices`）。

### Embedding 入口

使用命令行工具：

```bash
python tools/embedding_cli.py index --roles "Reshaely,VanlyShan,SolinXuan"
python tools/embedding_cli.py query --story-id future_academy_city --target-role Reshaely --roles "Reshaely,VanlyShan,SolinXuan" --query "chapter timeline" --top-k 4
```

默认 embedding 模型为 Ollama 的 `nomic-embed-text-v2-moe`。

### 图流程接入

当前 LangGraph 流程中接入了以下 RAG 节点：

1. `index_role_memories_for_rag`：规划前对记忆切片做向量化索引。
2. `retrieve_role_rag_contexts`：检索同框架下自身与其他角色记忆切片。
3. `generate_role_views`：将检索上下文注入角色生成提示词。
4. `finalize_output`：写入章节切片并刷新向量索引。

### 章节时间戳切片格式

角色生成切片写入路径：

`memory/<role_id>/<story_id>__chapter_<timestamp>_run<run_id>.md`

Header 包含字段：

- `Story ID`
- `Role ID`
- `Chapter Timestamp`
- `Run ID`
- `Topic`
- `Style`

## English

This folder documents the project RAG (Retrieval-Augmented Generation) layer.

### Runtime Storage

- Vector store path is configured by `RAG_CHROMA_DIR`.
- Default path: `.data/rag_chroma/` (git-ignored).
- Collection name is configured by `RAG_COLLECTION_NAME` (default: `story_memory_slices`).

### Embedding Entry

Use the CLI helper:

```bash
python tools/embedding_cli.py index --roles "Reshaely,VanlyShan,SolinXuan"
python tools/embedding_cli.py query --story-id future_academy_city --target-role Reshaely --roles "Reshaely,VanlyShan,SolinXuan" --query "chapter timeline" --top-k 4
```

Default embedding model: Ollama `nomic-embed-text-v2-moe`.

### Runtime Graph Integration

Current LangGraph pipeline includes:

1. `index_role_memories_for_rag`: embed and index memory slices before planning.
2. `retrieve_role_rag_contexts`: retrieve own and peer slices (same `story_id` preferred).
3. `generate_role_views`: inject retrieved context into role prompts.
4. `finalize_output`: persist chapter slices and refresh vector index.

### Chapter Timestamp Slice Format

Generated role slices are stored at:

`memory/<role_id>/<story_id>__chapter_<timestamp>_run<run_id>.md`

Header fields:

- `Story ID`
- `Role ID`
- `Chapter Timestamp`
- `Run ID`
- `Topic`
- `Style`
