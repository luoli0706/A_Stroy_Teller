# Flet UI

A lightweight user client for A Story Teller.

## Features

- Input form for `story_id`, `topic`, `style`, `roles`, `max_retry`
- Health-check button for Ollama readiness
- Real-time stream panel for node events and node logs
- Token stream panel for LLM token events
- Final story and quality report display
- Runtime metadata display (`run_id`, DB path, log path)
- Story history panel (load run records from SQLite)
- Role management panel (add/delete profile, add/delete memory slices)
- Export button to write current result into `opt/` as markdown and json
- Three-tab routing buttons for page switching:
	- Story Management
	- Role Management
	- Settings

## Run

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
