# A Story Teller / 智能故事生成系统

A Story Teller is a role-centered, multi-perspective storytelling system built with LangGraph + Ollama + ChromaDB.

A Story Teller 是一个基于 LangGraph + Ollama + ChromaDB 的角色中心、多视角智能故事生成系统。

It supports:

- Story framework loading and editing
- Role profile and memory slice management
- Single-role and multi-role story generation
- RAG retrieval from own and peer role memories under the same story framework
- Chapter timestamp memory slicing after each run
- Streaming events, logs, SQLite run history, and Flet desktop UI

它支持：

- 故事框架加载与编辑
- 角色设定与记忆切片管理
- 单角色/多角色故事生成
- 在同一故事框架下从自身与其他角色记忆切片进行 RAG 检索
- 生成后按章节时间戳写回记忆切片
- 流式事件、日志、SQLite 历史记录与 Flet 桌面 UI

## Features / 功能特性

- LangGraph pipeline with retry route and quality check
- Ollama local model routing (planner/role/integrator/quality/embedding)
- ChromaDB vector index for role memory slices
- Automatic chapter-slice persistence after generation
- Bilingual UI (Chinese/English)
- Story, role, and settings page separation in UI modules

- 基于 LangGraph 的可编排流程（含质检与重试）
- 本地 Ollama 多模型路由（规划/角色/整合/质检/嵌入）
- 角色记忆切片 ChromaDB 向量索引
- 生成完成后自动写回章节时间戳切片
- UI 支持中英切换
- UI 页面模块化解耦（故事/角色/设置）

## Project Structure / 项目结构

```text
A_Story_Teller/
  app/                      # Runtime graph, state, RAG, storage, observability
  UI/                       # Flet client
  role/                     # Role profiles
  memory/                   # Role memory slices
  stories/                  # Story frameworks
  tools/                    # CLI tools (role CLI, embedding CLI)
  docs/                     # Flow and API docs (bilingual)
  RAG/                      # RAG documentation
  .env.example              # Environment template
  requirements.txt          # Python dependencies
```

## Prerequisites / 环境准备

### 1) Python

- Python 3.11+ recommended

### 2) Ollama

Install and run Ollama locally, then pull required models:

```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text-v2-moe
```

本地安装并启动 Ollama，然后拉取所需模型：

```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text-v2-moe
```

## Installation / 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration / 配置

Copy environment template:

```bash
copy .env.example .env
```

Key settings in `.env`:

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL_PLANNER=qwen3.5:9b`
- `OLLAMA_MODEL_ROLE=qwen3.5:9b`
- `OLLAMA_MODEL_INTEGRATOR=qwen3.5:9b`
- `OLLAMA_MODEL_QUALITY=qwen3.5:9b`
- `OLLAMA_MODEL_EMBEDDING=nomic-embed-text-v2-moe`
- `RAG_ENABLED=true`
- `RAG_TOP_K=4`
- `RAG_CHROMA_DIR=.data/rag_chroma`
- `RAG_COLLECTION_NAME=story_memory_slices`

## Run CLI Pipeline / 命令行运行

Non-stream mode:

```bash
python -m app.main --story-id future_academy_city --topic "campus anomaly at night" --style cinematic --roles "Reshaely,VanlyShan,SolinXuan"
```

Stream mode:

```bash
python -m app.main --stream --story-id future_academy_city --topic "campus anomaly at night" --style cinematic --roles "Reshaely,VanlyShan,SolinXuan"
```

## Run UI / 启动 UI

```bash
python UI/flet_app.py
```

In UI, you can:

- Load/edit story frameworks
- Load/edit role profiles and memory slices
- Generate stories in single-role or multi-role mode
- Configure RAG settings and model endpoints from settings page

在 UI 中可进行：

- 故事框架加载与编辑
- 角色设定/记忆切片加载与编辑
- 单角色与多角色故事生成
- 在设置页控制 RAG 参数与模型配置

## RAG CLI / RAG 命令

Build vector index from memory slices:

```bash
python tools/embedding_cli.py index --roles "Reshaely,VanlyShan,SolinXuan"
```

Query RAG context:

```bash
python tools/embedding_cli.py query --story-id future_academy_city --target-role Reshaely --roles "Reshaely,VanlyShan,SolinXuan" --query "chapter timeline" --top-k 4
```

## Memory Slice Format / 记忆切片格式

Generated role slices are persisted as:

`memory/<role_id>/<story_id>__chapter_<timestamp>_run<run_id>.md`

Each slice header includes:

- Story ID
- Role ID
- Chapter Timestamp
- Run ID
- Topic
- Style

## Documentation / 文档索引

- `docs/flow.md` (pipeline flow / 流程说明)
- `docs/api.md` (module APIs / 接口说明)
- `RAG/README.md` (RAG usage / RAG 使用说明)
- `UI/README.md` (UI notes / UI 说明)
- `stories/README.md` (story framework workspace / 框架说明)

## License / 许可证

Licensed under the Apache License 2.0.

本项目采用 Apache License 2.0，详见 `LICENSE`。
