# A Story Teller 执行流程 (v0.2.5)

## 1. 启动与恢复 (Init & Recovery)
1. **Thread Check**: 系统根据 `thread_id` 检查 `AsyncSqliteSaver` 中是否有现有快照。
2. **Collect Requirements**: 加载演员名单与故事目标。

## 2. 剧组筹备 (Casting)
3. **Map Roles to Slots**: 独立节点根据演员性格分配故事位置（如：Reshaely -> 调查员）。
4. **Adapt Roles**: 演员生成故事特定身份（装备、短期目标）。
5. **Generate Relationships**: 编织初始关系网（如：A 对 B 存有戒心）。

## 3. 创作循环 (Iterative Generation)
6. **Parallel Generation**: **[Concurrency]** 并行触发各角色叙事。
7. **Integrate**: 融合视角产出正文。
8. **QA & Retry**: 结构化质检。若不通过则利用 Checkpoint 局部回滚重试。

## 4. 沉淀 (Finalize)
9. **Persist & Distill**: 生成内容追加到长期记忆，最终 Markdown 归档至 `opt/`。
