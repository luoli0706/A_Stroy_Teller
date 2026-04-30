# Changelog

本文件合并自 `docs/code_history.md`（代码变更）与 `docs/func_history.md`（功能演进），按版本倒序排列。

---

## [v0.3.2] - 2026-04-30

### 多 Provider 架构升级 (Multi-Provider Architecture)
- **Provider 抽象层**：新建 `app/llm/` 包，引入 `BaseLLMProvider` / `BaseEmbeddingProvider` ABC，支持依赖注入
- **Ollama / OpenAI / Anthropic 三 Provider**：通过 `LLM_PROVIDER` 环境变量切换后端
- **OpenAI Provider**：基于 `langchain-openai` ChatOpenAI，支持 JSON mode（response_format）
- **Anthropic Provider**：基于 `langchain-anthropic` ChatAnthropic，自动追加 JSON 输出指令
- **Embedding 回退**：Anthropic 无 Embedding API 时自动回退 Ollama；可通过 `EMBEDDING_PROVIDER` 显式覆盖
- **工厂函数**：`create_llm_provider()` / `create_embedding_provider()` / `create_story_client()` 替代全局单例

### 工程化加固 (Engineering Hardening)
- **移除模块级副作用**：`load_dotenv()` 从 `config.py` 模块级别移入 `init_config()` 显式调用
- **Prompt 模板外部化**：9 个 Prompt 模板提取到 `app/prompts/templates.py`
- **LLM 请求重试**：引入 tenacity 指数退避重试（`LLM_REQUEST_RETRY=3`）
- **依赖注入**：`StoryLLMClient` 接受 `BaseLLMProvider` 注入，去除全局单例

### 安全修复 (Security Fixes)
- **SQL 注入防护**：`metadata_store.query_metadata()` 新增 filter key 白名单校验
- **路径遍历防护**：`role_memory.py` 新增 `_validate_id()` 正则 + 分隔符检测
- **错误传播修复**：`robust_task` 返回 `Result[T]` 泛型类型，区分成功值与错误

### 代码质量 (Code Quality)
- **合并重复解析器**：新建 `app/markdown_utils.py` → `parse_markdown_header()`，合并 `metadata_extractor._parse_front_matter` 与 `chroma_memory._parse_header`
- **向下兼容**：保留 `get_story_client()` 别名和 `OllamaEmbeddingClient` 重导出

### 测试体系 (Testing)
- 新建 9 个 pytest 风格测试文件：`test_config.py`（重写）、`test_state.py`、`test_markdown_parser.py`、`test_sqlite_store.py`、`test_metadata_store.py`、`test_llm_providers.py`、`test_graph_nodes.py`、`test_role_memory.py`
- 新增 `conftest.py` 共享 fixtures（mock providers、temp db、sample state）

---

## [v0.3.1] - 2026-04-24

### 运行时与持久化一致性修复 (Runtime & Persistence Consistency)
- **Run ID 生命周期重构**：在 `collect_requirements` 阶段引入 `create_placeholder_run` 预分配 `run_id`，并在 `finalize_output` 使用 `update_story_run` 回写结果，消除既定事实索引与最终产物 `run_id` 不一致的问题
- **同步运行入口补齐**：`runtime.py` 新增 `run_story` 与 `stream_story_events` 同步封装，修复 CLI 入口调用与异步实现之间的接口断层
- **健康检查治理**：`llm_client.assert_ready` 不再吞异常，新增同步 `health_check` 封装以统一主入口可用性检查路径
- **生成任务编号前后一致**：CLI 可用性恢复，启动失败可感知

### RAG 与元数据协议收敛 (RAG & Metadata Protocol Alignment)
- **Chunk 全局唯一键**：`metadata_extractor` 的 `chunk_id` 升级为 `story_id + role_id + file_stem + chunk_index`，降低跨故事/跨角色碰撞风险
- **增量索引去重键修正**：`chroma_memory.index_memory_directory` 从 `slice_id` 对比改为 `doc_id(role::slice)` 对比，避免跨角色同名切片误判
- **Front Matter 标准化**：事实文件、世界观文件、角色切片统一采用 `---` 包裹并使用 `snake_case` 字段名
- **Header 兼容解析增强**：`_parse_header` 同时兼容旧版无分隔头和新版标准 front matter
- **向量过滤表达式规范化**：`retrieval_tools` 中 Chroma 检索过滤改为 `$and` 组合构建

### 类型安全与测试回归 (Type Safety & Test Regression)
- **Pydantic 可变默认值修复**：`StoryState`、`RoleStoryIdentity`、`QualityReport` 全面改为 `Field(default_factory=...)`
- **全流程测试更新**：`test_v030_full_pipeline.py` 对齐新 `run_id` 策略与头部字段命名

---

## [v0.3.0-alpha.3] - 2026-04-24

### 混合 RAG 架构演进 (Hybrid RAG Evolution)
- **元数据驱动检索**：引入独立的 `metadata.db`（SQLite WAL 模式），实现 Chunk 级别的元数据索引，支持基于角色、剧情时间锚点、叙事类型的精准物理定位
- **并行召回与评分融合**：重构检索引擎，实现 SQL 精准过滤与 Chroma 语义检索的并行召回，引入评分权重融合策略
- **强一致性落盘机制（Sequential Write-through）**：重写持久化逻辑，确保剧情生成落盘的同时索引数据自动同步到 SQLite 与向量库
- **智能分块读取（Smart Read with Citation）**：开发基于字节偏移的物理文件精准读取工具，支持带来源引用的片段输出，有效缓解 LLM 上下文压力并降低幻觉
- **从"相似"到"精准"的记忆召回**：混合检索使角色能准确区分"自己的回忆"与"世界事实"

### 核心逻辑重构 (Logic Refactoring)
- **RAG 节点演进**：`retrieve_role_rag_contexts` 节点完全接入混合检索路径，角色生成时自动参考"自身记忆 + 客观事实 + 世界观"
- **健壮性增强**：实现了 `metadata_extractor.py`，具备鲁棒的 Markdown Front Matter 解析能力
- **客观事实锚点**：引入"客观事实"与"世界观"双重锚点，确保所有角色多视角叙事在同一逻辑框架下进行
- **长文本处理优化**：通过智能分块读取，从容处理超长篇幅过往记忆

---

## [v0.1.0-alpha.2.5] - 2026-04-03 (Patch 1)

### 后端内核加固 (Backend Hardening)
- **异步持久化升级**：完成从同步 `SqliteSaver` 到 `AsyncSqliteSaver` 的迁移，完美适配全链路 `async/await` 架构
- **原生事件流捕获**：弃用手动回调，接入 `astream_events(v2)` 实时抓取全链路 Token 与节点状态，彻底解决"伪停滞"问题
- **数据库连接治理**：重构 `sqlite_store.py` 引入显式连接关闭逻辑，消除异步高并发下的 `ResourceWarning`
- **日志强制落盘**：优化 `observability.py` 增加 `flush()` 机制，确保异常中断时 `.log` 文件保留关键追溯信息

### 持久化可视化 (Persistence Visualization)
- **状态历史 API**：在 `runtime.py` 中新增 `get_thread_history_async`，利用 LangGraph 接口回溯持久化的 `StoryState` 快照
- **UI 框架适配**：针对 Flet 0.80+ 进行全面字符串化兼容性重构
- **无畏停滞的实时反馈**：通过后端原生流式技术，生成过程实时无损反馈到前端

---

## [v0.1.0-alpha.2.4] - 2026-04-02

### 创作保障 (Reliability)
- **断点续写功能**：引入"创作保险丝"，如果生成过程崩溃或被中断，使用相同"会话 ID"可从上次中断处继续，无需消耗额外算力和时间
- **接入 SqliteSaver**：利用 LangGraph 内置 Checkpointer 将图节点状态持久化到 SQLite
- **Thread ID 机制**：重构 `runtime.py` 支持会话标识符
- **数据库连接池优化**：使用显式 `try...finally: conn.close()` 结构消除资源泄露风险

---

## [v0.1.0-alpha.2.3] - 2026-04-02

### 系统健壮性与工程化 (Hardening)
- **集成测试构建**：新增 `tests/test_v023_ice_wind.py` 完整覆盖多角色入驻全流程逻辑
- **兼容性修复**：修复 Pydantic V2 弃用方法（`model_dump` 替换 `dict`），优化异步环境下事件循环检查
- **并发容错机制**：引入 `robust_task` 包装器，确保多角色并行生成时个别角色异常不会导致整图崩溃
- **全链路类型安全**：重构 `StoryState` 为基于 Pydantic 的模型，引入 `RoleStoryIdentity` 与 `QualityReport` 结构化子模型
- **增量 RAG 索引**：实现基于 SHA-256 内容哈希的增量索引机制，大幅优化存在大量过往记忆时的"索引冷启动"耗时

### 角色逻辑深化 (Role Logic)
- **独立映射节点**：将演员到槽位的映射逻辑从大纲节点剥离，建立独立的 `map_roles_to_slots` 节点
- **关系网引擎**：新增 `generate_relationships_async`，在故事开始前自动生成角色间初始社交关系矩阵
- **性格保真度增强**：在所有视角生成 Prompt 中强化通用性格（Real Identity）的权重要求
- **动态社交关系**：演员入驻故事后，系统根据背景自动推演角色间初始关系

---

## [v0.1.0-alpha.2.2] - 2026-04-02

### 角色扮演架构 (Roleplay Engine)
- **动态身份适配**：在 LLM 客户端新增 `adapt_role_to_framework_async`，支持根据通用性格生成故事相关的特定身份（JSON 模式）
- **槽位系统实现**：重构故事框架结构，引入 `Role Slots` 定义
- **状态机扩展**：更新 `StoryState` 以支持 `role_story_identities` 字段

### UI 深度重构 (UI Refactoring)
- **左右分栏布局**：UI 调整为响应式分栏结构，左侧统筹输入与实时日志，右侧专注结果呈现
- **组件化同步**：完善 `StoryControlPanel` 与主应用的异步状态同步
- **通用演员机制**：演员可带着固定性格标签跨入任何题材的故事
- **自动身份演化**：系统根据剧情大纲为每位演员自动生成符合背景的特定目标与装备

---

## [v0.1.0-alpha.2.1] - 2026-04-02

### 数据模型变更 (Data Model)
- **通用角色设定（Generic Profiles）**：重构 `role/` 下的角色设定结构，剥离特定故事背景。引入"基础形象""性格特质""语言风格"等通用字段
- **角色映射蓝图（Role Mapping）**：规划"演员-槽位"映射逻辑，为后续动态替换故事角色名奠定基础
- **从角色到演员**：角色不再受限于特定故事，拥有独立人格、外貌与语言风格

---

## [v0.1.0-alpha.2] - 2026-04-02

### 架构解耦与组件化 (Componentization)
- **UI 组件化重构**：`flet_app.py` 拆分为 `UI/components/` 目录下的独立组件类
- **结构化输出支持**：重构 `OllamaStoryClient` 支持 JSON 格式响应
- **人机协作（HITL）占位**：引入 `wait_for_user_outline` 节点，确立中断与恢复协作范式
- **界面模块化**：日志查看与故事生成控制分离，提升操作直观性
- **结构化质检反馈**：质检结果以结构化形式呈现（含分数、具体冲突点与修正建议）

### 工程化与自动化 (Automation)
- **自动记忆蒸馏**：新增 `distill_memories` 节点，实现生成内容自动汇总与长期记忆追加
- **测试框架建立**：引入 `unittest` 并在 `tests/` 目录下编写配置和 LLM 客户端单元测试
- **动态记忆演进**：系统自动将每次生成的精彩片段浓缩并追加到角色长期记忆汇总中

---

## [v0.1.0-alpha.1] - 2026-04-02

### 技术栈与性能 (Stack & Performance)
- **全异步重构**：所有 LangGraph 节点转换为 `async def`，使用 `graph.astream` 进行事件推送
- **并行视角生成**：在 `generate_role_views` 节点引入 `asyncio.gather` 并发触发多角色 LLM 请求
- **RAG 引擎升级**：接入 ChromaDB 原生 `query` 接口，支持 `where` 子句元数据过滤
- **配置中心化**：创建 `app/config.py` 统筹全局环境变量与生成参数
- **库标准化**：全面移除 `urllib` 手写代码，由异步库 `httpx` 统筹网络请求

### 架构解耦 (Decoupling)
- **UI 异步桥接**：`UI/flet_app.py` 通过 `app/runtime.py` 异步迭代器驱动，界面与业务隔离
- **模型客户端隔离**：`OllamaStoryClient` 封装所有 LLM 与 Embedding 异步细节
- **多视角并行**：多名角色同时撰写各自视角，确保视角生成的相对独立性与公平性
- **章节化管理**：生成的角色产出按照 `<story_id>__chapter_<timestamp>` 规则自动分类存储
- **多语言支持**：初步建立 I18N 体系，支持中英双语切换

---

## [v0.0.1-prototype]
- 同步模式下的单节点 LangGraph
- 基于 `urllib` 的手写 LLM 交互
- 散乱的 `os.getenv` 硬编码
- 基本的主题生成功能
- 基础的角色 Profile 加载
- 简单的 Flet UI 界面
