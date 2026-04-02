# A Story Teller 系统流程说明 (Alpha 0.1)

## 1. 核心架构设计
系统采用 **LangGraph (Async)** 结合 **Ollama** 实现多视角叙事。核心亮点在于 **全异步执行** 与 **并行视角生成**。

## 2. 图编排流程 (Graph Flow)

### 2.1 初始化阶段 (Init)
1. **collect_requirements (Async)**: 统一加载配置，执行 Ollama 健康检查。
2. **load_story_framework (Async)**: 按 ID 加载故事背景。
3. **load_roles (Async)**: 加载指定角色的 Profile 并存入 SQLite 以供追溯。
4. **index_role_memories_for_rag (Async)**: 批量更新指定角色的向量库。

### 2.2 叙事阶段 (Narrative)
5. **plan_global_story (Async)**: 生成全局故事大纲。
6. **retrieve_role_rag_contexts (Async)**: **[Parallel]** 并行为各角色从自身及同僚记忆中提取相关上下文。
7. **generate_role_views (Async)**: **[Concurrency Boost]** 使用 `asyncio.gather` 同时触发所有角色的视角生成。

### 2.3 整合与质检阶段 (Quality)
8. **integrate_perspectives (Async)**: 整合各角色视角产出最终正文。
9. **quality_check (Async)**: 进行一致性检查。若失败且未达到 `MAX_RETRY` 次数，则回退至视角生成节点。

### 2.4 归档阶段 (Archive)
10. **finalize_output (Async)**:
    - 将各角色产出作为新记忆持久化到 `memory/{role_id}/`。
    - 将最终成果按故事 ID 归档至 `opt/stories/{story_id}/`。

## 3. 并发策略
在 `generate_role_views` 节点，系统会根据 `roles` 列表的长度并发调用 LLM。这极大缩短了多角色生成时的总耗时。
