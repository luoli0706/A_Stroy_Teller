# Stories Framework

This folder stores reusable story frameworks.

## Layout

- `stories/default/framework.md`: fallback framework
- `stories/<story_id>/framework.md`: framework for a specific story line
- `stories/future_academy_city/framework.md`: 中文未来学园都市框架示例

## How it is used

- Graph state field `story_id` picks a framework directory.
- Node `load_story_framework` loads the matching framework text.
- Planner uses the framework text to constrain outline generation.

Example:

```bash
python -m app.main
```

Then pass `story_id` in graph input when needed.
