# 代码更新历史 (Code History)

## [v0.3.0-alpha.3] - 2026-04-24
### 混合 RAG 架构演进 (Hybrid RAG Evolution)
- **元数据驱动检索**：引入独立的 `metadata.db` (SQLite WAL模式)，实现了 Chunk 级别的元数据索引，支持基于角色、剧情时间锚点、叙事类型的精准物理定位。
- **并行召回与评分融合**：重构检索引擎，实现了 SQL 精准过滤与 Chroma 语义检索的并行召回，并引入评分权重融合策略，显著提升了跨章剧情的召回率与准确性。
- **强一致性落盘机制 (Sequential Write-through)**：重写持久化逻辑，确保剧情生成落盘的同时，索引数据自动同步到 SQLite 与向量库，且支持冷启动时的元数据自愈。
- **智能分块读取 (Smart Read with Citation)**：开发了基于字节偏移的物理文件精准读取工具，支持带来源引用的片段输出，有效缓解了 LLM 的上下文压力并大幅降低了幻觉。

### 核心逻辑重构 (Logic Refactoring)
- **RAG 节点演进**：`retrieve_role_rag_contexts` 节点完全接入混合检索路径，角色生成时自动参考“自身记忆 + 客观事实 (__facts__) + 世界观 (__world__)”，彻底消除了之前的角色记忆循环依赖。
- **健壮性增强**：实现了 `metadata_extractor.py`，具备鲁棒的 Markdown Front Matter 解析能力，并修复了在处理异常格式文件时的越界错误。

---

## [v0.1.0-alpha.2.5] - 2026-04-03 (Patch 1)
### 后端内核加固 (Backend Hardening)
- **异步持久化升级**：完成从同步 `SqliteSaver` 到 `AsyncSqliteSaver` 的迁移，完美适配全链路 `async/await` 架构。
- **原生事件流捕获**：弃用手动回调，接入 `astream_events(v2)` 实时抓取全链路 Token 与节点状态，彻底解决“伪停滞”问题。
- **数据库连接治理**：重构 `sqlite_store.py` 引入显式连接关闭逻辑，消除了异步高并发下的 `ResourceWarning` 资源泄露。
- **日志强制落盘**：优化 `observability.py` 增加 `flush()` 机制，确保在程序异常中断时，`.log` 文件仍能保留关键追溯信息。

### 持久化可视化 (Persistence Visualization)
- **状态历史 API**：在 `runtime.py` 中新增 `get_thread_history_async`，利用 LangGraph 接口回溯持久化的 `StoryState` 快照。
- **UI 框架适配**：针对 Flet 0.80+ 进行了全字符串化的兼容性重构（图标、颜色、弃用 API）。

---

## [v0.1.0-alpha.2.4] - 2026-04-02
### 持久化与断点续写 (Persistence)
- **接入 SqliteSaver**：利用 LangGraph 内置的 Checkpointer 机制，将图的每一个节点状态持久化到 SQLite 中。
- **Thread ID 机制**：重构 `runtime.py` 以支持会话标识符，允许系统根据 ID 恢复未完成的创作任务。
- **数据库连接池优化**：彻底重构 `app/sqlite_store.py`，使用显式的 `try...finally: conn.close()` 结构，消除了高并发下的资源泄露风险。

### UI 层交互增强
- **会话管理支持**：UI 增加 Thread ID 输入项，并在日志中实时反馈节点快照的保存状态。

---

## [v0.1.0-alpha.2.3] - 2026-04-02
### 系统健壮性与工程化 (Hardening)
- **集成测试构建**：新增 `tests/test_v023_ice_wind.py` 完整覆盖多角色入驻“冰与风之行”的全流程逻辑。
- **兼容性修复**：修复了 Pydantic V2 弃用方法（`model_dump` 替换 `dict`），并优化了异步环境下的 `assert_ready` 事件循环检查，确保了底层库升级和异步调用的稳定性。
- **并发容错机制**：引入 `robust_task` 包装器，确保多角色并行生成时，个别角色的异常不会导致整图流程崩溃。
- **全链路类型安全**：重构 `StoryState` 为基于 Pydantic 的模型，引入 `RoleStoryIdentity` 与 `QualityReport` 结构化子模型。
- **增量 RAG 索引**：实现基于 SHA-256 内容哈希的增量索引机制，大幅优化了存在大量过往记忆时的“索引冷启动”耗时。

### 角色逻辑深化 (Role Logic)
- **独立映射节点**：将演员到槽位的映射逻辑从大纲节点剥离，建立独立的 `map_roles_to_slots` 节点。
- **关系网引擎**：新增 `generate_relationships_async`，在故事开始前自动生成角色间的初始社交关系矩阵。
- **性格保真度增强**：在所有视角生成 Prompt 中强化了对通用性格（Real Identity）的权重要求。

---

## [v0.1.0-alpha.2.2] - 2026-04-02
### 角色扮演架构 (Roleplay Engine)
- **动态身份适配**：在 LLM 客户端中新增 `adapt_role_to_framework_async`，支持根据通用性格生成故事相关的特定身份（JSON 模式）。
- **槽位系统实现**：重构故事框架结构，引入 `Role Slots` 定义。在 `plan_global_story` 中初步实现演员到槽位的映射。
- **状态机扩展**：更新 `StoryState` 以支持 `role_story_identities` 字段，确保身份信息在并行生成节点间正确流转。

### UI 深度重构 (UI Refactoring)
- **左右分栏布局**：将 UI 调整为响应式分栏结构，左侧统筹输入与实时日志，右侧专注结果呈现。
- **组件化同步**：进一步完善 `StoryControlPanel` 与主应用的异步状态同步。

---

## [v0.1.0-alpha.2.1] - 2026-04-02
### 数据模型变更 (Data Model)
- **通用角色设定 (Generic Profiles)**：重构了 `role/` 下的角色设定结构，剥离了特定故事背景。引入了“基础形象”、“性格特质”、“语言风格”等通用字段。
- **角色映射蓝图 (Role Mapping)**：在蓝图中规划了“演员-槽位”映射逻辑，为后续动态替换故事角色名奠定基础。

---

## [v0.1.0-alpha.2] - 2026-04-02
### 架构解耦与组件化 (Componentization)
- **UI 组件化重构**：将 `flet_app.py` 拆分为 `UI/components/` 目录下的独立组件类（`LogViewer`, `StoryControlPanel`），实现了视图与控制逻辑的初步分离。
- **结构化输出支持**：重构 `OllamaStoryClient` 以支持 JSON 格式响应，为自动化质检和数据解析奠定了基础。
- **人机协作 (HITL) 占位**：在 Graph 中引入 `wait_for_user_outline` 节点，确立了中断与恢复的协作范式。

### 工程化与自动化 (Automation)
- **自动记忆蒸馏**：新增 `distill_memories` 节点，实现了生成内容的自动汇总与长期记忆追加。
- **测试框架建立**：引入 `unittest` 并在 `tests/` 目录下编写了针对配置加载和异步 LLM 客户端的单元测试。

---

## [v0.1.0-alpha.1] - 2026-04-02
### 技术栈与性能 (Stack & Performance)
- **全异步重构**：将所有 LangGraph 节点转换为 `async def`，使用 `graph.astream` 进行事件推送。
- **并行视角生成**：在 `generate_role_views` 节点引入 `asyncio.gather` 并发触发多角色的 LLM 请求。
- **RAG 引擎升级**：接入 ChromaDB 原生 `query` 接口，支持 `where` 子句元数据过滤。
- **配置中心化**：创建 `app/config.py` 统筹全局环境变量与生成参数。
- **库标准化**：全面移除 `urllib` 手写代码，由异步库 `httpx` 统筹网络请求。

### 架构解耦 (Decoupling)
- **UI 异步桥接**：`UI/flet_app.py` 现通过 `app/runtime.py` 异步迭代器驱动，实现界面与业务的彻底隔离。
- **模型客户端隔离**：`OllamaStoryClient` 现封装了所有 LLM 与 Embedding 异步细节，Graph 不再关心底层请求实现。

---

## [v0.0.1-prototype]
- 同步模式下的单节点 LangGraph。
- 基于 `urllib` 的手写 LLM 交互。
- 散乱的 `os.getenv` 硬编码。
