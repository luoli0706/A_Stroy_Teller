# Stories Framework / 故事框架

## 中文

该目录用于存放可复用的故事框架。

### 目录结构

- `stories/default/framework.md`：默认回退框架
- `stories/<story_id>/framework.md`：指定故事线框架
- `stories/future_academy_city/framework.md`：未来学园都市中文框架示例

### 使用方式

- 图状态字段 `story_id` 用于选择框架目录。
- `load_story_framework` 节点会加载对应框架文本。
- `plan_global_story` 会使用框架约束生成主线。

示例：

```bash
python -m app.main
```

需要时在输入参数中传入 `story_id`。

## English

This folder stores reusable story frameworks.

### Layout

- `stories/default/framework.md`: fallback framework
- `stories/<story_id>/framework.md`: framework for a specific story line
- `stories/future_academy_city/framework.md`: Chinese "Future Academy City" sample

### How It Is Used

- Graph state field `story_id` selects a framework directory.
- Node `load_story_framework` loads the matching framework text.
- `plan_global_story` uses the framework to constrain outline generation.

Example:

```bash
python -m app.main
```

Pass `story_id` in input when needed.
