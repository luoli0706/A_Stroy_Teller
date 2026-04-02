# 版本更新历史 (Version History)

## [v0.1.0-alpha.1] - 2026-04-02
### 核心变更 (Core Changes)
- **高性能并行架构**：引入 `asyncio` 全异步节点重构，多角色视角生成由顺序执行改为 `asyncio.gather` 并发执行，大幅提升生成效率。
- **RAG 引擎重构**：弃用手写相似度计算，接入 ChromaDB 原生 `query` 接口，并引入 `story_id` 元数据过滤（Metadata Filtering），查询效率提升至 O(log N)。
- **配置中心化**：新建 `app/config.py` 统筹管理所有路径、模型选型、环境变量及生成参数，彻底移除代码中的硬编码。
- **UI 逻辑解耦**：`UI/flet_app.py` 重写为异步版本，通过 `app/runtime.py` 的异步流式接口与业务逻辑交互，界面响应更流畅。

### 优化与修复 (Optimizations & Fixes)
- **库方法标准化**：全面使用 `httpx` 替换 `urllib` 手写调用，提升网络请求的鲁棒性。
- **存储结构优化**：明确了 `memory/`（角色长期记忆）与 `opt/stories/`（归档产物）的职责，支持按故事 ID 分类存储。
- **Embedding 批量化**：优化了 Ollama 嵌入客户端，支持批量文本向量化。

---

## [v0.0.1-prototype] - 2026-03-XX
### 初始功能
- 基于 LangGraph 的基础故事生成流程。
- 支持角色 Profile 加载。
- 基础的 Flet UI 原型。
- 单节点顺序执行。
