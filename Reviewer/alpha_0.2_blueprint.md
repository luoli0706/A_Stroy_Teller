# A Story Teller Alpha 0.2 版本蓝图

## 1. 版本目标
Alpha 0.2 的核心目标是 **“人机协同与知识深化”**。在 0.1 版本稳固的并行架构基础上，引入用户介入机制，并优化角色长期记忆的演进逻辑。

## 2. 核心任务清单

### 2.1 用户介入机制 (Human-in-the-Loop)
- [ ] **大纲干预节点**：在 `plan_global_story` 之后新增 `wait_for_user_outline` 节点。用户可以在 UI 中修改生成的大纲，并点击“确认”后继续后续生成。
- [ ] **视角调整回路**：在 `generate_role_views` 之后，允许用户对个别角色的视角进行微调或要求针对特定角色重写。

### 2.2 角色记忆演进 (Memory Distillation)
- [ ] **记忆摘要（Summary）自动更新**：在 `finalize_output` 阶段，自动汇总本次生成的角色切片，并将其融入角色的长期背景文件 `{role_id}_summary.md`。
- [ ] **时间线一致性锚点**：引入 `Timeline Anchor` 概念。系统自动提取各角色视角中的关键事实（如：Reshaely 在 12:00 到达图书馆），形成共享的事实数据库，防止角色间出现硬性时空矛盾。

### 2.3 UI 组件化重构 (UI Componentization)
- [ ] **模块化解耦**：将 `flet_app.py` 中庞大的组件拆分为 `UI/components/` 下的独立类（例如 `StoryControl`, `LogViewer`, `ConfigPanel`）。
- [ ] **状态同步优化**：引入简单的事件总线或状态存储，解决 UI 中多选角色、动态更新配置时的状态同步问题。

### 2.4 工程化增强 (Engineering Hardening)
- [ ] **容错并发**：优化 `asyncio.gather` 的异常处理，确保单角色 LLM 生成超时或失败时不崩溃，而是触发该角色的独立重试。
- [ ] **结构化质检器**：重构 `quality_check_async` 的 Prompt，输出 JSON 格式的质检报告（包含分数、冲突详情、具体修正建议）。

## 3. 技术路线
1. **交互增强**：利用 LangGraph 的 `interrupt` 能力实现人机协作。
2. **逻辑分层**：引入 `Service 层` 来处理复杂的记忆总结与事实提取，保持 Graph 节点的简洁。

## 4. 后续评估计划
开发完成后，将生成：
1. **Alpha 0.2 人机协作效率评估**：重点对比“全自动”与“有人干预”模式下的故事质量差异。
2. **Alpha 0.2 记忆一致性评估**：评估跨章节后的角色记忆继承效果。
