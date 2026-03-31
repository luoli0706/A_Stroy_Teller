# A Story Teller API

## 1. 当前 API 形态

当前项目以 Python 模块 API 为主（非 HTTP 服务）。

## 2. Graph API

文件：`app/graph.py`

### 2.1 build_graph()

- 说明：构建并返回编译后的 LangGraph。
- 返回：可执行图实例。

## 3. Role API

文件：`app/role_memory.py`

### 3.1 discover_roles(base_dir)

- 输入：`base_dir`（角色根目录）
- 返回：角色 ID 列表（目录名）

### 3.2 load_role_assets(base_dir, roles)

- 输入：角色根目录与角色列表
- 返回：角色资产映射
  - profile: 角色设定文本
  - memory: 角色记忆文本

## 4. SQLite API

文件：`app/sqlite_store.py`

### 4.1 init_db(db_path=DEFAULT_DB_PATH)

- 作用：初始化数据库和表结构。
- 返回：数据库路径字符串。

### 4.2 upsert_role_asset(role_id, profile, memory, db_path=DEFAULT_DB_PATH)

- 作用：插入或更新角色资产到 role_assets。

### 4.3 insert_story_run(topic, style, roles_json, integrated_draft, final_story, db_path=DEFAULT_DB_PATH)

- 作用：写入一条故事运行记录到 story_runs。
- 返回：新记录的 run_id。

## 5. 运行接口

文件：`app/main.py`

执行命令：

```bash
python -m app.main
```

输出内容：

- 每个角色的视角稿
- 整合后的故事
- SQLite 落库后的 run_id 和 db 路径

## 6. 规划中的 HTTP API（建议）

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
