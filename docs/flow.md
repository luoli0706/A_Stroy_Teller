# A Story Teller Flow

## 1. 流程总览

当前系统采用 LangGraph 编排，围绕角色中心的多视角叙事进行生成。

主流程：

1. collect_requirements
2. load_story_framework
3. load_roles
4. plan_global_story
5. generate_role_views
6. integrate_perspectives
7. quality_check
8. finalize_output

图路径：

`START -> collect_requirements -> load_story_framework -> load_roles -> plan_global_story -> generate_role_views -> integrate_perspectives -> quality_check -> finalize_output -> END`

流式能力：

- 通过 `python -m app.main --stream` 启用。
- 按节点输出更新事件（JSON 行），便于 UI 实时渲染流程进度。

## 2. 节点职责

### 2.1 collect_requirements

- 读取输入参数（topic/style/roles）。
- 自动发现 role 目录中的角色（当输入未显式提供 roles 时）。
- 初始化 SQLite 数据库。
- 执行 Ollama 启动健康检查（服务可达 + 模型存在）。

### 2.2 load_story_framework

- 按 `story_id` 从 `stories/<story_id>/framework.md` 加载故事框架。
- 未命中时自动回退到 `stories/default/framework.md`。

### 2.3 load_roles

- 读取每个角色的 profile.md 与记忆切片目录。
- 从 `memory/<role_id>/*.md` 聚合角色记忆切片。
- 将角色资产写入 SQLite 的 role_assets 表（upsert）。

### 2.4 plan_global_story

- 生成全局剧情框架（global_outline）。
- 调用 Ollama 规划模型，在故事框架约束下生成三幕式主线和共享事实。

### 2.5 generate_role_views

- 在统一 global_outline 下，按角色分别生成视角稿。
- 每个角色调用 Ollama 角色模型，结合 profile 与 memory 输出角色视角。
- 输出 role_view_drafts（role_id -> text）。

### 2.6 integrate_perspectives

- 将多角色视角稿整合为 integrated_draft。
- 调用 Ollama 整合模型，输出统一正文。

### 2.7 quality_check

- 调用 Ollama 质检模型进行一致性和角色区分度评估。
- 输出 quality_report（PASS/FAIL + 关键问题 + 修改建议）。
- 当结果为 FAIL 且 `retry_count <= max_retry` 时，自动回到 `generate_role_views` 重试。

### 2.8 finalize_output

- 生成 final_story。
- 将整次运行写入 SQLite 的 story_runs 表。
- 返回 run_id 作为追踪标识。

## 3. 文件与数据布局

### 3.1 角色目录

```
role/
  Reshaely/
    profile.md
  VanlyShan/
    profile.md
  SolinXuan/
    profile.md
```

### 3.2 记忆切片目录

```
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
```

### 3.3 SQLite

默认数据库路径：`.data/story_teller.db`

核心表：

- role_assets: 角色设定与记忆快照
- story_runs: 每次故事生成运行记录

### 3.4 环境配置

- `.env`：本地配置文件，不被 git 跟踪。
- `.env.example`：配置模板，受 git 跟踪。
- 默认 Ollama 地址：`http://127.0.0.1:11434`
- 默认模型：`qwen3.5:9b`

### 3.5 故事框架目录

```
stories/
  default/
    framework.md
  urban_detective/
    framework.md
```

## 4. 后续扩展建议

1. 在 quality_check 后增加条件路由，FAIL 时触发自动重写回路。
2. 将 role memory 更新回写到 `memory/<role_id>/<story_id>.md` 与 SQLite，形成长期记忆闭环。
3. 增加角色并行与限流策略，提升多角色生成性能。

## 5. 脚本组织

统一脚本目录：`scripts/`

- `scripts/test_role_ops.py`：角色设定/记忆增删接口测试与初始化样例。

CLI 封装目录：`tools/`

- `tools/role_cli.py`：角色设定/记忆接口命令行封装。
