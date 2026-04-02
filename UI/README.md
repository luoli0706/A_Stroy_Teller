# Flet UI / Flet Client

## 中文

轻量级 A Story Teller 图形客户端。

### 功能

- 故事管理面板：
	- 故事框架查询/加载与在线编辑
	- 角色名字加载与角色快速选择
	- 单角色生成与多角色生成
	- 单角色生成后可自动写入角色记忆切片
	- 输入项：`story_id`、`topic`、`style`、`roles`、`max_retry`
- Ollama 健康检查
- 节点与日志实时事件流
- LLM token 流展示
- 最终故事与质量报告展示
- 运行元信息展示（`run_id`、数据库路径、日志路径）
- 历史运行记录面板（读取 SQLite）
- 角色管理面板：
	- 按角色名字查询设定（角色 ID 不清楚时可用）
	- 按名字加载角色到编辑区
	- 角色列表一键加载
	- 记忆切片子标签加载/编辑
	- 角色设定与记忆切片增删改
- 一键导出到 `opt/`（markdown + json）
- 三页面路由切换：故事管理 / 角色管理 / 设置
- 设置页中英文切换
- 各页面支持滚动

### 运行

```bash
python UI/flet_app.py
```

或：

```bash
flet run UI/flet_app.py
```

模块方式：

```bash
python -m UI.flet_app
```

## English

Lightweight desktop client for A Story Teller.

### Features

- Story management panel:
	- Story framework query/load with inline editing
	- Role-name loading and quick role selection
	- Single-role and multi-role generation actions
	- Single-role generation can persist generated slices to role memory
	- Inputs: `story_id`, `topic`, `style`, `roles`, `max_retry`
- Ollama health check
- Realtime node-event and log stream
- LLM token stream view
- Final story and quality report view
- Runtime metadata (`run_id`, DB path, log path)
- Story history panel (SQLite)
- Role management panel:
	- Query role profile by role name when role ID is unknown
	- Load role by name into editor
	- One-click load buttons in role list
	- Memory-slice sub-tabs for loading/editing
	- Add/update/delete role profile and memory slices
- One-click export to `opt/` (markdown + json)
- Three main route pages: Story / Roles / Settings
- Built-in language switch (Chinese / English)
- Scroll support on each page

### Run

```bash
python UI/flet_app.py
```

Or:

```bash
flet run UI/flet_app.py
```

Module form:

```bash
python -m UI.flet_app
```
