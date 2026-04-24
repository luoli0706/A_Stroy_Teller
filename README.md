# A Story Teller / 智能故事生成系统 (v0.3.1)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)

**A Story Teller** 是一个以角色为中心、多视角协同创作、具备全链路持久化能力的智能故事生成系统。系统输入“故事框架 + 多角色模板”，基于 LangGraph 和混合索引 RAG 生成高一致性的多角色故事。

---

## 核心特性

### 1. 角色槽位映射与身份适配
- **框架槽位映射**：根据故事框架将多个角色模板分配到对应剧情槽位。
- **动态身份适配**：角色保留核心性格，并在当前故事框架中生成临时身份与目标。
- **关系矩阵生成**：在多角色视角生成前构建关系网，提升角色互动一致性。

### 2. LangGraph 全链路编排
- **全异步状态图**：核心流程由 `StateGraph` 驱动，支持节点级流式事件输出。
- **并行角色生成**：角色适配与视角生成支持并发执行，减少总时延。
- **质量回路**：支持质量检查与条件路由重试。

### 3. 既定事实锚点 + 混合 RAG
- **事实锚点机制**：先从全局大纲抽取 `established_facts` 与 `world_bible`，再用于后续角色生成与章节整合。
- **混合检索**：结合 Chroma 语义检索与 SQLite 元数据过滤，实现“角色私有记忆 + 客观事实”联合召回。
- **增量索引**：基于内容哈希，仅对变更切片做增量更新。

### 4. 持久化与可追溯性
- **节点快照**：`AsyncSqliteSaver` 持久化图状态，可用于历史回溯与续跑验证。
- **统一产物协议**：事实文件、角色切片与最终故事均按统一头部字段落盘。
- **运行记录闭环**：预分配 `run_id` 并在收尾阶段回写，确保索引与产物编号一致。

---

## 技术栈

| 模块 | 选型 |
| :--- | :--- |
| **调度内核** | LangGraph (Async StateGraph + Checkpoint) |
| **模型推理** | Ollama (本地私有化部署) |
| **向量检索** | ChromaDB |
| **结构检索** | SQLite Metadata (`metadata.db`) |
| **数据模型** | Pydantic V2 (强类型校验) |
| **前端交互** | Flet (响应式三栏布局) |
| **底层通信** | HTTPX (全链路异步) |

---

## 快速开始

### 1. 环境安装
```bash
git clone https://github.com/luoli0706/A_Stroy_Teller.git
cd A_Stroy_Teller
pip install -r requirements.txt
```

### 2. 启动推理引擎
确保本地 [Ollama](https://ollama.com/) 已启动，并拉取所需模型：
```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text-v2-moe
```

### 3. 运行应用
```bash
# 启动 UI
python UI/flet_app.py

# 运行 v0.3 全流程集成测试
python -m unittest tests/test_v030_full_pipeline.py

# CLI 运行示例
python -m app.main --story-id cat_world --roles Reshaely,VanlyShan,SolinXuan --stream
```

---

## 项目结构
```text
├── app/                # 核心逻辑 (图编排、LLM 客户端、混合 RAG)
├── UI/                 # 组件化表现层
├── stories/            # 故事框架模板库
├── role/               # 角色模板
├── memory/             # 角色跨剧本长期记忆
├── opt/                # 最终故事与归档产物
└── docs/               # 详细的技术与功能演进历史
```

## 开发者说明
- 当前版本：`v0.3.1`
- 版本演进：参见 `docs/code_history.md` 与 `docs/func_history.md`
- 仍在持续改进项：长链路流式稳定性、断点续写自动恢复验证、Pydantic 新 API 迁移

## 许可证
Apache License 2.0
