# A Story Teller Flow

## 1. 流程总览

当前系统采用 LangGraph 编排，围绕角色中心的多视角叙事进行生成。

主流程：

1. collect_requirements
2. load_roles
3. plan_global_story
4. generate_role_views
5. integrate_perspectives
6. finalize_output

图路径：

`START -> collect_requirements -> load_roles -> plan_global_story -> generate_role_views -> integrate_perspectives -> finalize_output -> END`

## 2. 节点职责

### 2.1 collect_requirements

- 读取输入参数（topic/style/roles）。
- 自动发现 role 目录中的角色（当输入未显式提供 roles 时）。
- 初始化 SQLite 数据库。

### 2.2 load_roles

- 读取每个角色的 profile.md 与 memory.md。
- 将角色资产写入 SQLite 的 role_assets 表（upsert）。

### 2.3 plan_global_story

- 生成全局剧情框架（global_outline）。
- 当前是占位策略，后续可接入 Ollama 进行真实规划。

### 2.4 generate_role_views

- 在统一 global_outline 下，按角色分别生成视角稿。
- 输出 role_view_drafts（role_id -> text）。

### 2.5 integrate_perspectives

- 将多角色视角稿整合为 integrated_draft。
- 当前是规则拼接，后续可替换为 LLM 整合节点。

### 2.6 finalize_output

- 生成 final_story。
- 将整次运行写入 SQLite 的 story_runs 表。
- 返回 run_id 作为追踪标识。

## 3. 文件与数据布局

### 3.1 角色目录

```
role/
  alice/
    profile.md
    memory.md
  bob/
    profile.md
    memory.md
```

### 3.2 SQLite

默认数据库路径：`.data/story_teller.db`

核心表：

- role_assets: 角色设定与记忆快照
- story_runs: 每次故事生成运行记录

## 4. 后续扩展建议

1. 使用 Ollama 替换 plan_global_story / generate_role_views / integrate_perspectives 占位逻辑。
2. 在 quality_check 节点补充跨角色冲突检测。
3. 将 role memory 更新回写到 memory.md 与 SQLite，形成长期记忆闭环。
