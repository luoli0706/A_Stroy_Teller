# A Story Teller / 智能故事生成系统 (v0.3.2)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)

**A Story Teller** 是一个以角色为中心、多视角协同创作、具备全链路持久化能力的智能故事生成系统。系统输入"故事框架 + 多角色模板"，基于 LangGraph 和混合索引 RAG 生成高一致性的多角色故事。

---

## 核心特性

### 1. 多 Provider LLM 后端 (v0.3.2)
- **Provider 抽象层**：统一接口支持 Ollama / OpenAI / Anthropic 三套 LLM 后端
- **即插即用**：通过 `LLM_PROVIDER` 环境变量切换，无需修改代码
- **智能回退**：Anthropic 无 Embedding API 时自动回退 Ollama / OpenAI Embedding
- **向下兼容**：原有 Ollama 环境变量完全保留

### 2. 角色槽位映射与身份适配
- **框架槽位映射**：根据故事框架将多个角色模板分配到对应剧情槽位
- **动态身份适配**：角色保留核心性格，在当前故事框架中生成临时身份与目标
- **关系矩阵生成**：在多角色视角生成前构建关系网，提升角色互动一致性

### 3. LangGraph 全链路编排
- **全异步状态图**：核心流程由 `StateGraph` 驱动，支持节点级流式事件输出
- **并行角色生成**：角色适配与视角生成支持并发执行，减少总时延
- **质量回路**：支持质量检查与条件路由重试
- **LLM 请求重试**：指数退避自动重试（tenacity），提升鲁棒性

### 4. 既定事实锚点 + 混合 RAG
- **事实锚点机制**：先从全局大纲抽取 `established_facts` 与 `world_bible`，再用于后续角色生成与章节整合
- **混合检索**：结合 Chroma 语义检索与 SQLite 元数据过滤，实现"角色私有记忆 + 客观事实"联合召回
- **增量索引**：基于内容哈希，仅对变更切片做增量更新

### 5. 持久化与可追溯性
- **节点快照**：`AsyncSqliteSaver` 持久化图状态，可用于历史回溯与续跑验证
- **统一产物协议**：事实文件、角色切片与最终故事均按统一头部字段落盘
- **运行记录闭环**：预分配 `run_id` 并在收尾阶段回写，确保索引与产物编号一致

---

## 技术栈

| 模块 | 选型 |
| :--- | :--- |
| **调度内核** | LangGraph (Async StateGraph + Checkpoint) |
| **模型推理** | Ollama / OpenAI / Anthropic (可切换) |
| **向量检索** | ChromaDB |
| **结构检索** | SQLite Metadata (`metadata.db`) |
| **数据模型** | Pydantic V2 (强类型校验) |
| **前端交互** | Flet (响应式三栏布局) |
| **底层通信** | HTTPX (全链路异步) |
| **重试机制** | Tenacity (指数退避) |

---

## 快速开始

### 1. 环境安装
```bash
git clone https://github.com/luoli0706/A_Stroy_Teller.git
cd A_Stroy_Teller
pip install -r requirements.txt
```

### 2. 配置 Provider

复制并编辑环境配置：
```bash
cp .env.example .env
```

**Ollama（默认，本地）**：
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL_PLANNER=qwen3.5:9b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text-v2-moe
```

**OpenAI**：
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL_PLANNER=gpt-4o
```

**Anthropic**：
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_PLANNER=claude-sonnet-4-20250514
# Embedding 自动回退 Ollama，也可显式指定：
# EMBEDDING_PROVIDER=openai
```

### 3. 启动推理引擎（Ollama）
```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text-v2-moe
```

### 4. 运行应用
```bash
# CLI 运行
python -m app.main --story-id urban_detective --roles Reshaely,VanlyShan,SolinXuan

# 流式输出
python -m app.main --story-id cat_world --roles Reshaely,VanlyShan,SolinXuan --stream

# 启用 RAG
python -m app.main --story-id urban_detective --rag-enabled true --rag-top-k 4

# 切换 Provider（通过环境变量）
LLM_PROVIDER=openai python -m app.main --story-id urban_detective --stream

# 启动 UI
python UI/flet_app.py
```

---

## 项目结构
```text
├── app/                    # 核心逻辑
│   ├── main.py             # CLI 入口
│   ├── config.py           # 配置中心（多 Provider）
│   ├── state.py            # Pydantic 状态模型
│   ├── graph.py            # LangGraph 图编排（16 节点）
│   ├── runtime.py          # 运行封装（同步/异步/流式）
│   ├── llm_client.py       # StoryLLMClient（Provider 无关层）
│   ├── story_framework.py  # 故事框架加载
│   ├── role_memory.py      # 角色与记忆文件管理
│   ├── observability.py    # 日志与观测
│   ├── markdown_utils.py   # 统一 Markdown 解析
│   ├── retrieval_tools.py  # 混合检索（Chroma + SQL）
│   ├── metadata_extractor.py  # 元数据提取
│   ├── sqlite_store.py     # 运行记录存储
│   ├── metadata_store.py   # 块元数据存储
│   ├── llm/                # Provider 抽象层
│   │   ├── base.py         # ABC 接口
│   │   ├── ollama.py       # Ollama Provider
│   │   ├── openai.py       # OpenAI Provider
│   │   ├── anthropic.py    # Anthropic Provider
│   │   ├── ollama_embed.py # Ollama Embedding
│   │   ├── openai_embed.py # OpenAI Embedding
│   │   └── factory.py      # Provider 工厂
│   ├── prompts/            # Prompt 模板
│   │   └── templates.py    # 9 个故事生成 Prompt
│   └── rag/                # RAG 子系统
│       ├── chroma_memory.py # 向量索引与检索
│       └── ollama_embedding.py # 兼容层
├── tests/                  # 测试套件
│   ├── conftest.py         # pytest fixtures
│   ├── test_config.py      # 配置测试
│   ├── test_state.py       # 状态模型测试
│   ├── test_markdown_parser.py    # Markdown 解析器测试
│   ├── test_sqlite_store.py       # SQLite CRUD 测试
│   ├── test_metadata_store.py     # 元数据存储测试
│   ├── test_llm_providers.py      # Provider 测试
│   ├── test_graph_nodes.py        # 图节点测试
│   ├── test_role_memory.py        # 角色操作测试
│   └── test_v030_full_pipeline.py # 全流程集成测试
├── UI/                     # 组件化表现层（Flet）
├── stories/                # 故事框架模板库
├── role/                   # 角色模板
├── memory/                 # 角色跨剧本长期记忆
├── opt/                    # 最终故事与归档产物
├── docs/                   # 技术文档与变更历史
│   ├── CHANGELOG.md        # 版本变更日志
│   ├── code_history.md     # 代码演进历史
│   ├── func_history.md     # 功能演进历史
│   └── blueprint.md        # 架构蓝图
├── tools/                  # CLI 工具
├── scripts/                # 辅助脚本
├── .env.example            # 环境配置模板
└── requirements.txt        # Python 依赖
```

---

## 环境变量参考

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `ollama` | LLM 后端：ollama / openai / anthropic |
| `EMBEDDING_PROVIDER` | (自动) | Embedding 后端，空则跟随 LLM_PROVIDER |
| **Ollama** | | |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL_PLANNER` | `qwen3.5:9b` | 主线规划模型 |
| `OLLAMA_MODEL_ROLE` | `qwen3.5:9b` | 角色叙述模型 |
| `OLLAMA_MODEL_INTEGRATOR` | `qwen3.5:9b` | 整合模型 |
| `OLLAMA_MODEL_QUALITY` | (跟随 INTEGRATOR) | 质检模型 |
| `OLLAMA_MODEL_EMBEDDING` | `nomic-embed-text-v2-moe` | 嵌入模型 |
| **OpenAI** | | |
| `OPENAI_API_KEY` | — | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 地址（支持代理） |
| `OPENAI_MODEL_PLANNER` | `gpt-4o` | 主线规划模型 |
| `OPENAI_MODEL_EMBEDDING` | `text-embedding-3-small` | 嵌入模型 |
| **Anthropic** | | |
| `ANTHROPIC_API_KEY` | — | Anthropic API 密钥 |
| `ANTHROPIC_MODEL_PLANNER` | `claude-sonnet-4-20250514` | 主线规划模型 |
| **通用** | | |
| `OLLAMA_TEMPERATURE` | `0.7` | 生成温度（所有 Provider 共用） |
| `MAX_RETRY` | `1` | 质量回路最大重试次数 |
| `LLM_REQUEST_RETRY` | `3` | 单次 LLM 请求最大重试次数 |
| `RAG_ENABLED` | `true` | 是否启用 RAG |
| `RAG_TOP_K` | `4` | 每个角色 RAG 检索条数 |
| `RAG_COLLECTION_NAME` | `story_memory_slices` | Chroma 向量集合名 |

---

## 开发者说明
- 当前版本：`v0.3.2`
- 版本演进：参见 `docs/CHANGELOG.md`
- Provider 可选依赖：`langchain-openai`、`langchain-anthropic`（仅在切换对应 Provider 时需要）
- 仍在持续改进项：长链路流式稳定性、断点续写自动恢复验证、Pydantic 新 API 迁移

## 许可证
Apache License 2.0
