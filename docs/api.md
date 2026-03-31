# A Story Teller API

## 1. 当前 API 形态

当前项目以 Python 模块 API 为主（非 HTTP 服务）。

## 2. Graph API

文件：`app/graph.py`

### 2.1 build_graph()

- 说明：构建并返回编译后的 LangGraph。
- 返回：可执行图实例。

### 2.2 节点调用关系

- `collect_requirements`：读取输入、初始化 SQLite，并执行 Ollama 启动健康检查。
- `load_story_framework`：按 story_id 加载 stories 框架文本。
- `load_roles`：加载角色 profile/memory 并同步入库。
- `plan_global_story`：调用 LLM 生成主线。
- `generate_role_views`：调用 LLM 生成多角色视角文本。
- `integrate_perspectives`：调用 LLM 生成整合文本。
- `quality_check`：调用 LLM 输出 PASS/FAIL 质检报告。
- `quality_check -> generate_role_views`：当 FAIL 且未超过 max_retry 时自动重试。
- `finalize_output`：落库运行记录并返回 run_id。

## 3. LLM API

文件：`app/llm_client.py`

### 3.1 get_story_client()

- 返回：缓存的 `OllamaStoryClient` 单例。

### 3.2 OllamaStoryClient.health_check()

- 作用：检查 Ollama 服务可达性与配置模型是否已拉取。

### 3.3 OllamaStoryClient.assert_ready()

- 作用：在启动阶段强制校验，失败时抛出运行时错误。

### 3.4 OllamaStoryClient.plan_global_story(topic, style, role_ids, framework)

- 作用：使用规划模型在指定故事框架约束下输出全局大纲。

### 3.5 OllamaStoryClient.generate_role_view(role_id, profile, memory, outline, style)

- 作用：按角色 profile + memory 生成单角色视角叙述。

### 3.6 OllamaStoryClient.integrate_perspectives(topic, style, role_drafts)

- 作用：整合多角色视角为统一故事文本。

### 3.7 OllamaStoryClient.quality_check(outline, integrated_story, role_ids)

- 作用：输出质量检查报告（PASS/FAIL + 建议）。

## 4. Role API

文件：`app/role_memory.py`

### 4.1 discover_roles(base_dir)

- 输入：`base_dir`（角色根目录）
- 返回：角色 ID 列表（仅包含存在 `profile.md` 的角色目录）

### 4.2 load_role_assets(base_dir, roles, memory_dir="memory")

- 输入：角色根目录、角色列表、独立记忆目录
- 返回：角色资产映射
  - profile: 角色设定文本
  - memory: 角色记忆切片聚合文本

### 4.3 add_role_profile(role_id, profile_text, role_dir="role")

- 作用：新增或覆盖角色设定文件 `role/<role_id>/profile.md`。

### 4.4 delete_role_profile(role_id, role_dir="role")

- 作用：删除角色设定文件。

### 4.5 add_role_memory_slice(role_id, story_id, memory_text, memory_dir="memory")

- 作用：新增或覆盖单个故事记忆切片 `memory/<role_id>/<story_id>.md`。

### 4.6 delete_role_memory_slice(role_id, story_id, memory_dir="memory")

- 作用：删除指定故事记忆切片。

### 4.7 delete_all_role_memories(role_id, memory_dir="memory", role_dir="role")

- 作用：删除角色全部记忆切片，并兼容清理旧路径 `role/<role_id>/memory.md`。

## 5. SQLite API

文件：`app/sqlite_store.py`

### 4.1 init_db(db_path=DEFAULT_DB_PATH)

- 作用：初始化数据库和表结构。
- 返回：数据库路径字符串。

### 4.2 upsert_role_asset(role_id, profile, memory, db_path=DEFAULT_DB_PATH)

- 作用：插入或更新角色资产到 role_assets。

### 4.3 insert_story_run(topic, style, roles_json, integrated_draft, final_story, db_path=DEFAULT_DB_PATH)

- 作用：写入一条故事运行记录到 story_runs。
- 返回：新记录的 run_id。

## 6. 环境变量 API 合约

`.env` 为本地运行配置（已在 `.gitignore` 中忽略），`.env.example` 为提交模板。

默认值：

- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL_PLANNER=qwen3.5:9b`
- `OLLAMA_MODEL_ROLE=qwen3.5:9b`
- `OLLAMA_MODEL_INTEGRATOR=qwen3.5:9b`
- `OLLAMA_MODEL_QUALITY=qwen3.5:9b`
- `OLLAMA_TEMPERATURE=0.7`

## 7. 运行接口

文件：`app/main.py`
核心运行模块：`app/runtime.py`

执行命令：

```bash
python -m app.main
```

流式执行命令：

```bash
python -m app.main --stream
```

参数化运行示例：

```bash
python -m app.main --story-id urban_detective --topic "midnight archive theft" --style noir --roles "Reshaely,VanlyShan,SolinXuan" --max-retry 2
```

参数化流式示例：

```bash
python -m app.main --story-id urban_detective --topic "midnight archive theft" --style noir --roles "Reshaely,VanlyShan,SolinXuan" --max-retry 2 --stream
```

输出内容：

- 每个角色的视角稿
- 整合后的故事
- SQLite 落库后的 run_id 和 db 路径

流式输出内容：

- 每个节点的更新事件（JSON 行）
- 字段包括：`event`、`node`、`keys`、`data`

输入参数可选增加：

- `story_id`：故事框架标识，映射到 `stories/<story_id>/framework.md`。
- `topic`：故事主题。
- `style`：叙事风格。
- `roles`：逗号分隔角色 ID 列表。
- `max_retry`：质检失败后的最大重试次数。
- `stream`：启用节点级流式输出（适合 UI 实时展示）。

### 7.1 Runtime API

文件：`app/runtime.py`

- `build_input_state(...)`：构建标准化输入状态。
- `run_story(state)`：非流式一次性执行，返回最终状态。
- `stream_story_events(state)`：流式执行，产出节点事件 + token 事件迭代器。

### 7.2 监控与日志

- 控制台日志：运行时输出节点开始/结束、重试、run_id 等信息。
- 文件日志：自动写入 `logs/run_<timestamp>.log`。
- 关键字段：`node`、`stage`、`pid`、`retry_count`、`run_id`。
- 实现模块：`app/observability.py`（创建运行级 logger，同时挂载 console/file handler）。

### 7.3 流式事件类型

- `token`：LLM token 增量事件。
  - 字段：`event`, `node`, `model`, `role_id`, `text`
- `node_update`：LangGraph 节点状态更新。
  - 字段：`event`, `node`, `keys`, `data`
- `done`：流程流式结束标记。
- `error`：流式执行错误。

## 8. 脚本

脚本统一放置在 `scripts/` 文件夹。

- `scripts/test_role_ops.py`
  - 测试删除 `alice` 和 `bob` 的角色设定与记忆。
  - 新增角色 `Reshaely`、`VanlyShan`、`SolinXuan` 的设定。
  - 新增多故事记忆切片，写入 `memory/<role_id>/`。

## 9. CLI 封装（独立文件夹）

角色接口已封装为命令行工具，单独放在 `tools/` 文件夹：

- `tools/role_cli.py`

常用命令：

```bash
python tools/role_cli.py list-roles
python tools/role_cli.py add-profile Reshaely --file role/Reshaely/profile.md
python tools/role_cli.py delete-profile alice
python tools/role_cli.py add-memory SolinXuan case_001 --text "- clue A\n- clue B"
python tools/role_cli.py delete-memory SolinXuan case_001
python tools/role_cli.py delete-all-memory bob
```

## 10. 规划中的 HTTP API（建议）

后续可在 `app/api/` 下增加 FastAPI，并暴露以下接口：

- `POST /stories/generate`
  - 输入：topic/style/roles
  - 输出：final_story、role_view_drafts、run_id

- `GET /stories/runs/{run_id}`
  - 输出：指定运行记录

- `GET /roles`
  - 输出：角色列表及最新资产摘要

- `POST /roles/{role_id}/memory`
  - 输入：memory patch
  - 输出：更新后的角色记忆

当前版本尚未实现 HTTP API，本文件记录的是已实现模块 API 与下一步服务化方向。
