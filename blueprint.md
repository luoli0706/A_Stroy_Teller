# A Story Teller Blueprint

## 1. 项目定位

### 1.1 项目目标

A Story Teller 是一个以 LangGraph 为核心编排框架的故事生成系统，目标是从「用户灵感」到「可发布故事」形成可追踪、可迭代、可扩展的生产流程。

核心目标：

- 将故事创作拆分为可控节点，而不是一次性黑盒生成。
- 在生成质量与稳定性之间取得平衡，支持重复运行与结果对比。
- 支持后续扩展为多风格、多语言、多角色工作流。

### 1.2 核心价值

- 对用户：用更低门槛把想法变成结构完整的故事。
- 对开发：通过图结构明确每一步职责，便于优化与测试。
- 对产品：可逐步接入更多能力，如角色记忆、世界观库、审核与发布。

## 1.3 可行性结论（本次讨论）

针对"本地 Ollama + 角色中心 + 多视角叙事 + 主节点整合"的方案，结论是：

- 技术可行：LangGraph 天然适合把"全局规划"和"角色叙述"拆成独立节点并编排。
- 架构可扩展：后续增加新角色时，可按配置动态扩容角色节点或角色循环。
- 成本可控：本地 Ollama 无需外部 API 成本，适合离线或私有化场景。
- 风险可管理：主要风险是上下文长度、角色间事实冲突、推理耗时，可通过状态压缩、冲突检查和并行策略缓解。

## 1.4 [v0.3] 策略变更：既定事实驱动的 RAG 与章节化整合

### 1.4.1 旧策略问题

旧策略中 RAG 的时机与目标：各角色在生成自己的故事时，通过 RAG 检索**其他角色的记忆切片**以确保逻辑融洽。

这种方式存在以下问题：

1. **循环依赖**：Role A 的生成质量依赖 Role B 的既有记忆切片，但首次运行时这些切片并不存在，导致 RAG 检索为空，各视角完全独立。
2. **跨角色主观偏差**：即便有历史切片，其他角色的叙事是主观视角，并非客观事实；以此作为参照可能引入新的矛盾。
3. **上下文窗口溢出**：主节点整合时需要同时接收所有角色的完整草稿，角色数量或篇幅增加时极易超出 LLM 上下文限制。

### 1.4.2 新策略：既定事实（Established Facts）作为共享锚点

**核心思路**：

- **维护一条故事主线**（全局大纲已完成），但在此基础上进一步提炼出**既定事实时间线（Established Facts）**和**世界观设定（World Bible）**。
- 既定事实是客观的、角色无关的事件序列，是所有角色必须遵从的"剧情真相"。
- 世界观设定描述故事背景、规则和氛围。

**RAG 的新时机与目的**：

| 阶段 | RAG 来源 | 目的 |
|------|----------|------|
| `generate_established_facts` | 无 RAG，由 LLM 从大纲提炼 | 生成客观事实锚点 |
| `index_facts_for_rag` | 将既定事实写入向量库 | 为角色生成阶段提供可检索的权威参照 |
| `retrieve_role_rag_contexts` | **检索既定事实 + 世界观**（而非其他角色切片） | 给每个角色相同的客观上下文 |
| `generate_role_views` | 使用 RAG 检索结果 | 角色填充主观体验、细节与情感，但不违背既定事实 |
| `integrate_perspectives` | 既定事实按章节切分 | 章节化整合，解决上下文窗口问题 |

**章节化整合策略**：

整合节点不再一次性合并所有角色草稿，而是：
1. 将既定事实按幕/章节切分（Act 1 / Act 2 / Act 3 或时间戳段落）。
2. 对每个章节，将相关角色片段与该章节事实一起发送给 LLM。
3. 输出各章节故事段落，最终拼接为完整故事。

这样，无论角色数量或篇幅如何增加，单次 LLM 调用的上下文量始终可控。

### 1.4.3 策略变更的可行性评估

| 维度 | 评估 |
|------|------|
| 技术可行性 | ✅ LangGraph 节点扩展简单，ChromaDB 支持 doc_type 元数据过滤 |
| 逻辑一致性提升 | ✅ 消除循环依赖，各角色基于同一客观事实生成 |
| 上下文窗口 | ✅ 章节化整合将单次上下文量降至可控范围 |
| 向后兼容 | ✅ `retrieve_role_rag_contexts` 在既定事实缺失时回退到旧的角色记忆检索 |
| 新增复杂度 | ⚠️ 新增 2 个节点（generate_established_facts、index_facts_for_rag），流程延长约 1-2 次 LLM 调用 |
| 首次运行效果 | ✅ 不再依赖历史记忆，首次运行即可获得逻辑融洽的故事 |

## 1.5 本次需要修改的核心点

1. 模型层：默认 provider 从云 API 调整为本地 Ollama。
2. 状态层：从单一 `draft` 升级为"全局故事状态 + 角色视角状态集合"。
3. 存储层：为每个角色建立独立设定文档与记忆文档。
4. 流程层：新增"主线规划节点""角色叙述节点（多角色）""主节点整合"。
5. 评估层：新增"跨角色一致性"与"角色声音区分度"指标。
6. **[v0.3] 既定事实节点**：新增 `generate_established_facts` 和 `index_facts_for_rag`，重构 RAG 检索策略，章节化整合。


## 2. 用户与场景设定

### 2.1 目标用户

- 轻创作者：有点子，但不会搭建完整剧情。
- 内容运营：需要批量产出主题故事素材。
- 教育场景：用于写作练习与创意思维训练。

### 2.2 核心使用场景

1. 快速草稿：输入主题和风格，得到 1 个可读短篇。
2. 定向重写：保留剧情骨架，仅切换叙事风格。
3. 分阶段创作：先大纲，再扩写，再润色，最后输出。

## 3. 产品范围

### 3.1 MVP 范围

- 输入：主题、风格、篇幅、受众、角色列表。
- 流程：主线规划 -> 多角色叙述 -> 主节点整合 -> 质量检查 -> 输出。
- 输出：标题、全局摘要、各角色视角文本、融合正文、可选续写钩子。

### 3.2 非 MVP（后续）

- 长篇多章管理。
- 角色与世界观长期记忆。（基础版本已接入 RAG）
- 人工反馈闭环与偏好学习。
- Web 前端与多端分发。

## 4. LangGraph 架构蓝图

### 4.1 状态模型（State）建议

建议在图中维护统一状态，示例字段：

- `input_topic`: 用户主题
- `input_style`: 文风偏好
- `input_length`: 目标篇幅
- `audience`: 目标受众
- `roles`: 角色清单（每个角色包含 id/name/role_type）
- `world_bible`: 世界观与全局设定
- `global_outline`: 全局分幕大纲
- `role_profiles`: 角色设定集合（目标、秘密、关系网）
- `role_memories`: 角色记忆索引（文档路径或内存对象）
- `role_view_drafts`: 各角色视角草稿（map: role_id -> text）
- `rag_role_contexts`: 各角色检索到的 RAG 上下文
- `integrated_draft`: 主节点整合后的正文
- `quality_report`: 质量检查结果
- `final_story`: 最终输出
- `chapter_timestamp`: 本次章节时间戳
- `memory_slice_paths`: 本次写入的角色记忆切片路径
- `metadata`: token、耗时、模型版本

### 4.2 节点职责建议

1. `collect_requirements`
作用：标准化用户输入，填充默认值。

2. `load_role_assets`
作用：加载角色设定文档与记忆文档，注入状态。

3. `plan_global_story`
作用：产出全局主线与关键事件时间轴。

4. `generate_role_view`
作用：每个角色基于同一主线与 RAG 检索上下文分别叙述自己的视角。

5. `integrate_perspectives`
作用：主节点整合各角色叙述，消解冲突并形成统一正文。

6. `quality_check`
作用：检查逻辑一致性、跨角色事实冲突、重复段落、安全内容。

7. `finalize_output`
作用：输出最终文本与附加信息，并写入章节记忆切片。

8. `index_role_memories_for_rag`
作用：将角色记忆切片嵌入写入 Chroma 向量库。

9. `retrieve_role_rag_contexts`
作用：按角色检索同框架记忆切片（自身 + 其他角色）并形成提示词上下文。

### 4.3 路由与分支

- 正常路径：`START -> collect_requirements -> load_role_assets -> index_role_memories_for_rag -> plan_global_story -> retrieve_role_rag_contexts -> generate_role_view(多角色) -> integrate_perspectives -> quality_check -> finalize_output -> END`
- 失败回路：当 `quality_check` 不通过时，回到 `integrate_perspectives` 或触发指定角色重写，并设置最大重试次数。
- 可选分支：当用户指定“只要角色视角草稿”时，在 `generate_role_view` 后提前结束。

### 4.4 角色中心设计（关键）

角色作为一等公民（first-class unit），每个角色至少有两类文档：

- 角色设定文档：静态信息，如身份、背景、说话风格、禁忌、目标。
- 角色记忆文档：动态信息，如已发生事件、角色认知偏差、关系变化。

建议目录：

```
role/
  Reshaely/
    profile.md
  VanlyShan/
    profile.md
  SolinXuan/
    profile.md

memory/
  Reshaely/
    case_library_midnight.md
    case_clocktower_signal.md
  VanlyShan/
    case_library_midnight.md
    case_clocktower_signal.md
  SolinXuan/
    case_library_midnight.md
    case_clocktower_signal.md

tools/
  role_cli.py

scripts/
  test_role_ops.py

opt/
  # 输出结果目录
```

说明：

- `profile.md` 偏稳定，人工或工具编辑。
- `memory/<role_id>/*.md` 为记忆切片，按故事与章节时间戳管理。
- 所有角色共享同一个 `global_outline`，但叙述时引用自己的记忆切片集合。

章节切片推荐命名：

- `<story_id>__chapter_<UTC_TIMESTAMP>_run<run_id>.md`

## 5. 技术方案建议

### 5.1 代码结构（建议）

```
app/
  main.py                 # 入口
  graph.py                # 图编排
  llm_client.py           # Ollama 调用封装
  state.py                # TypedDict/Pydantic 状态定义
  role_memory.py          # 角色设定/记忆接口
  sqlite_store.py         # SQLite 持久化
role/
  <role_id>/
    profile.md
memory/
  <role_id>/
    <story_id>.md
tools/
  role_cli.py             # 角色接口 CLI 封装
scripts/
  test_role_ops.py        # 接口测试脚本
opt/
  # 输出结果目录
tests/
  test_graph_smoke.py
  test_nodes.py
```

### 5.2 依赖建议

- 已有：`langgraph`, `langchain-core`, `python-dotenv`
- 可选补充：
  - `langchain-ollama`（本地 Ollama 模型接入）
  - `chromadb`（向量检索）
  - `pydantic`（严格状态验证）
  - `pytest`（测试）

### 5.3 配置建议

环境变量建议：

- `MODEL_PROVIDER`：固定为 `ollama`
- `OLLAMA_BASE_URL`：默认 `http://127.0.0.1:11434`
- `OLLAMA_MODEL_*`：默认 `qwen3.5:9b`
- `OLLAMA_MODEL_EMBEDDING`：默认 `nomic-embed-text-v2-moe`
- `OLLAMA_MODEL_PLANNER`：主线规划模型名
- `OLLAMA_MODEL_ROLE`：角色叙述模型名
- `OLLAMA_MODEL_INTEGRATOR`：整合模型名
- `RAG_ENABLED`：是否启用 RAG
- `RAG_TOP_K`：每名角色检索条数
- `RAG_CHROMA_DIR`：向量库目录
- `RAG_COLLECTION_NAME`：向量集合名
- `MAX_RETRY`：质量回路最大次数
- `MAX_PARALLEL_ROLES`：角色并行上限
- `LOG_LEVEL`：日志等级

## 5.4 Ollama 落地要点

- 进程管理：启动前检查本地 Ollama 服务可用性。
- 模型策略：规划/角色/整合可先共用一个模型，后续按任务拆分模型。
- 性能策略：角色叙述节点可并行，但需限制并发避免本机过载。
- 容错策略：当模型响应失败时，支持角色级重试，不阻断整图。

## 6. 质量与评估

### 6.1 评估指标

- 结构完整性：剧情是否有清晰起承转合。
- 一致性：角色设定、时间线、叙述视角是否一致。
- 风格命中：是否符合用户指定文风。
- 可读性：句长分布、段落节奏、重复率。
- 角色声音区分度：不同角色是否有明显语言风格差异。
- 跨角色事实一致性：同一事件在多视角下是否可对齐。

### 6.2 验证方式

- 单元测试：节点输入输出契约。
- 冒烟测试：整图最小流程可运行。
- 回归测试：固定输入对比关键质量指标变化。

## 7. 版本迭代路线

### v0.1（当前基础）

- 单节点写作示例跑通。

### v0.2（MVP）

- 接入本地 Ollama。
- 拆分为“主线 + 多角色 + 整合”流程。
- 增加质量检查与重试。

### v0.3（增强）

- 完成角色记忆文档自动更新。（已完成：章节时间戳切片）
- 支持角色增删与动态路由。
- 支持大纲模式与全文模式切换。

### v0.3.5（RAG）

- 增加 Chroma 向量检索。
- 增加 Ollama embedding 接口封装。
- 角色生成时可检索同框架下自身与其他角色记忆切片。

### v0.3.6（既定事实驱动 RAG + 章节化整合）[已实现]

- 新增 `generate_established_facts` 节点：从全局大纲提炼既定事实时间线与世界观设定。
- 新增 `index_facts_for_rag` 节点：将既定事实索引至 ChromaDB（doc_type 标记）。
- 重构 `retrieve_role_rag_contexts`：优先检索既定事实，消除角色间循环依赖。
- 重构 `integrate_perspectives`：章节化整合策略，每幕独立调用 LLM，解决上下文窗口问题。
- 状态新增字段：`established_facts`、`world_bible`、`story_chapters`、`rag_facts_indexed`。

### v0.4（产品化）

- 引入角色记忆与世界观配置。
- 提供简单 API 或 UI。

## 8. 当前仓库落地建议

建议先完成以下四步：

1. 通过 `tools/role_cli.py` 管理角色设定和记忆切片。
2. 在 `app/graph.py` 上增加质量检查失败后的重试回路。
3. 在 `opt/` 下增加运行导出（按 run_id 输出 markdown/json）。
4. 新增最小测试，覆盖单角色与双角色场景的冒烟运行。

---

本蓝图用于统一产品思路与技术实现，后续可以按版本逐段细化为开发任务清单。

## 9. English Summary

### 9.1 Product Positioning

A Story Teller is a LangGraph-based story production system that converts user inspiration into publishable narratives through traceable, iterative, and extensible workflow nodes.

Core goals:

- Replace one-shot black-box generation with controllable node-based creation.
- Balance output quality and runtime stability for repeatable runs.
- Scale to multi-style, multi-language, and multi-role pipelines.

### 9.2 Feasibility Conclusion

For the "local Ollama + role-centric + multi-perspective + master integration" strategy:

- Technically feasible with LangGraph node orchestration.
- Architecturally extensible for dynamic role growth.
- Cost-effective due to local model runtime.
- Main risks (context length, role fact conflicts, latency) can be mitigated by state compression, conflict checks, and parallel limits.

### 9.3 Scope

MVP includes:

- Inputs: topic, style, length, audience, role list.
- Flow: global planning -> role drafts -> integration -> quality check -> output.
- Outputs: title, summary, per-role drafts, integrated story, continuation hook.

Beyond MVP:

- Multi-chapter long-form management.
- Long-term role/world memory (base RAG support already integrated).
- Human feedback loop and preference learning.
- Multi-end product delivery.

### 9.4 State and Node Blueprint

Important state additions:

- `rag_role_contexts`, `chapter_timestamp`, `memory_slice_paths`.

Recommended/implemented nodes:

1. `collect_requirements`
2. `load_role_assets`
3. `plan_global_story`
4. `generate_role_view`
5. `integrate_perspectives`
6. `quality_check`
7. `finalize_output`
8. `index_role_memories_for_rag`
9. `retrieve_role_rag_contexts`

### 9.5 RAG and Memory Model

- Role profile is static (`role/<role_id>/profile.md`).
- Role memory is dynamic slices (`memory/<role_id>/*.md`).
- Retrieval uses same-framework priority, then role scope fallback.
- Generated chapter slices are persisted with timestamp naming:
  - `<story_id>__chapter_<UTC_TIMESTAMP>_run<run_id>.md`

### 9.6 Configuration and Dependencies

Key dependencies:

- `langgraph`, `langchain-core`, `python-dotenv`
- `langchain-ollama`, `chromadb`, `pydantic`, `pytest`

Key environment variables:

- Ollama runtime: `OLLAMA_BASE_URL`, `OLLAMA_MODEL_*`
- Embedding: `OLLAMA_MODEL_EMBEDDING=nomic-embed-text-v2-moe`
- RAG controls: `RAG_ENABLED`, `RAG_TOP_K`, `RAG_CHROMA_DIR`, `RAG_COLLECTION_NAME`

### 9.7 Quality and Evolution

Quality dimensions:

- Narrative completeness
- Role and timeline consistency
- Style adherence
- Readability and repetition control
- Role voice distinction

Version roadmap:

- v0.1 baseline
- v0.2 local Ollama + multi-node MVP
- v0.3 memory updates and dynamic routing
- v0.3.5 RAG integration
- v0.4 productization