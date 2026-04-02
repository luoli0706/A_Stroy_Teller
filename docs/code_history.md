# 代码更新历史 (Code History)

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
