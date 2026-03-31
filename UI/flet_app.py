import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import flet as ft

from app.llm_client import get_story_client
from app.role_memory import (
    add_role_memory_slice,
    add_role_profile,
    delete_all_role_memories,
    delete_role_memory_slice,
    delete_role_profile,
    discover_roles,
)
from app.runtime import build_input_state, stream_story_events
from app.sqlite_store import get_story_run, list_story_runs


def _compact_preview(value: Any, max_len: int = 220) -> str:
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len] + " ..."


def main(page: ft.Page) -> None:
    page.title = "A Story Teller - Flet Client"
    page.window_width = 1240
    page.window_height = 860
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#f7f8fb"

    story_id = ft.TextField(label="Story ID", value="urban_detective", width=220)
    topic = ft.TextField(label="Topic", value="midnight archive theft", expand=True)
    style = ft.TextField(label="Style", value="noir", width=180)
    roles = ft.TextField(
        label="Roles (comma-separated)",
        value="Reshaely,VanlyShan,SolinXuan",
        expand=True,
    )
    max_retry = ft.TextField(label="Max Retry", value="1", width=120)

    status_text = ft.Text("Idle", color="#444")
    health_text = ft.Text("Health: not checked", color="#555")
    run_meta_text = ft.Text("Run: -", selectable=True)
    ui_status_text = ft.Text("UI ready", color="#555")

    event_log = ft.ListView(expand=True, spacing=6, auto_scroll=True)
    history_log = ft.ListView(expand=True, spacing=6, auto_scroll=True)
    role_list = ft.ListView(expand=True, spacing=6, auto_scroll=True)
    token_stream = ft.TextField(
        label="Token Stream",
        multiline=True,
        min_lines=8,
        max_lines=18,
        read_only=True,
        value="",
    )
    final_story = ft.TextField(
        label="Final Story",
        multiline=True,
        min_lines=12,
        max_lines=22,
        read_only=True,
        value="",
    )
    quality_report = ft.TextField(
        label="Quality Report",
        multiline=True,
        min_lines=4,
        max_lines=8,
        read_only=True,
        value="",
    )

    run_button = ft.ElevatedButton("Run Story")
    check_button = ft.OutlinedButton("Health Check")
    export_button = ft.OutlinedButton("Export To opt")

    role_id_input = ft.TextField(label="Role ID", width=220)
    profile_input = ft.TextField(label="Role Profile", multiline=True, min_lines=5, max_lines=10)
    memory_story_id_input = ft.TextField(label="Memory Story ID", width=220)
    memory_text_input = ft.TextField(label="Memory Slice Text", multiline=True, min_lines=4, max_lines=8)

    history_limit = ft.TextField(label="History Limit", value="20", width=120)
    selected_run_text = ft.Text("Selected Run: none", selectable=True)

    final_state_holder: dict[str, Any] = {}

    def add_event_line(text: str, color: str = "#222") -> None:
        event_log.controls.append(ft.Text(text, size=12, color=color, selectable=True))
        page.update()

    def set_ui_status(text: str, color: str = "#555") -> None:
        ui_status_text.value = text
        ui_status_text.color = color
        page.update()

    def render_history() -> None:
        history_log.controls.clear()
        try:
            limit = int(history_limit.value.strip() or "20")
        except ValueError:
            limit = 20

        runs = list_story_runs(limit=limit)
        if not runs:
            history_log.controls.append(ft.Text("No story runs found.", color="#666"))
            page.update()
            return

        for run in runs:
            run_id = int(run.get("id", 0))
            title = f"#{run_id} | {run.get('created_at', '')} | {run.get('topic', '')}"

            def load_run(_: ft.ControlEvent, selected_id: int = run_id) -> None:
                data = get_story_run(selected_id)
                if not data:
                    set_ui_status(f"Run {selected_id} not found.", "#a21515")
                    return
                final_story.value = str(data.get("final_story", ""))
                quality_report.value = "Loaded from history; quality_report is not persisted in current schema."
                selected_run_text.value = (
                    f"Selected Run: {selected_id} | {data.get('created_at', '')} | style={data.get('style', '')}"
                )
                set_ui_status(f"Loaded run #{selected_id}", "#0f7a2a")
                page.update()

            history_log.controls.append(
                ft.Row(
                    [
                        ft.TextButton(text=title, on_click=load_run),
                        ft.Text(str(run.get("roles_json", "")), size=11, color="#5a6780"),
                    ],
                    wrap=True,
                )
            )
        page.update()

    def render_roles() -> None:
        role_list.controls.clear()
        role_ids = discover_roles("role")
        if not role_ids:
            role_list.controls.append(ft.Text("No roles found.", color="#666"))
            page.update()
            return

        for role_id in role_ids:
            role_list.controls.append(ft.Text(role_id, selectable=True))
        page.update()

    def handle_health(_: ft.ControlEvent) -> None:
        result = get_story_client().health_check()
        health_text.value = f"Health: {'OK' if result.ok else 'FAILED'} | {result.message}"
        health_text.color = "#0f7a2a" if result.ok else "#a21515"
        page.update()

    def handle_export(_: ft.ControlEvent) -> None:
        if not final_state_holder:
            set_ui_status("Nothing to export yet. Run a story first.", "#a21515")
            return

        opt_dir = Path("opt")
        opt_dir.mkdir(parents=True, exist_ok=True)
        run_id = final_state_holder.get("run_id")
        run_tag = str(run_id) if run_id is not None else datetime.now().strftime("%Y%m%d_%H%M%S")

        md_path = opt_dir / f"story_{run_tag}.md"
        json_path = opt_dir / f"story_{run_tag}.json"

        md_content = (
            f"# Story Export {run_tag}\n\n"
            f"- topic: {final_state_holder.get('topic', '')}\n"
            f"- style: {final_state_holder.get('style', '')}\n"
            f"- roles: {', '.join(final_state_holder.get('roles', []))}\n"
            f"- run_id: {final_state_holder.get('run_id', 'n/a')}\n"
            f"- log_file: {final_state_holder.get('log_file_path', 'n/a')}\n\n"
            "## Quality Report\n\n"
            f"{final_state_holder.get('quality_report', '')}\n\n"
            "## Final Story\n\n"
            f"{final_state_holder.get('final_story', '')}\n"
        )

        md_path.write_text(md_content, encoding="utf-8")
        json_path.write_text(
            json.dumps(final_state_holder, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        set_ui_status(f"Exported: {md_path} and {json_path}", "#0f7a2a")

    def handle_add_profile(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        if not role_id:
            set_ui_status("Role ID is required.", "#a21515")
            return
        profile_path = add_role_profile(role_id, profile_input.value)
        set_ui_status(f"Profile saved: {profile_path}", "#0f7a2a")
        render_roles()

    def handle_delete_profile(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        if not role_id:
            set_ui_status("Role ID is required.", "#a21515")
            return
        deleted = delete_role_profile(role_id)
        set_ui_status(f"Profile deleted={deleted} for {role_id}", "#0f7a2a" if deleted else "#a21515")
        render_roles()

    def handle_add_memory(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        story = memory_story_id_input.value.strip()
        if not role_id or not story:
            set_ui_status("Role ID and Memory Story ID are required.", "#a21515")
            return
        path = add_role_memory_slice(role_id, story, memory_text_input.value)
        set_ui_status(f"Memory saved: {path}", "#0f7a2a")

    def handle_delete_memory(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        story = memory_story_id_input.value.strip()
        if not role_id or not story:
            set_ui_status("Role ID and Memory Story ID are required.", "#a21515")
            return
        deleted = delete_role_memory_slice(role_id, story)
        set_ui_status(f"Memory deleted={deleted} for {role_id}/{story}", "#0f7a2a" if deleted else "#a21515")

    def handle_delete_all_memories(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        if not role_id:
            set_ui_status("Role ID is required.", "#a21515")
            return
        count = delete_all_role_memories(role_id)
        set_ui_status(f"Deleted memory slices={count} for {role_id}", "#0f7a2a")

    def run_worker() -> None:
        run_button.disabled = True
        status_text.value = "Running..."
        status_text.color = "#1f4e8c"
        event_log.controls.clear()
        token_stream.value = ""
        final_story.value = ""
        quality_report.value = ""
        run_meta_text.value = "Run: starting"
        page.update()

        try:
            role_list = [item.strip() for item in roles.value.split(",") if item.strip()]
            state = build_input_state(
                story_id=story_id.value.strip() or "default",
                topic=topic.value.strip() or "an unexpected friendship",
                style=style.value.strip() or "warm",
                roles=role_list,
                max_retry=int(max_retry.value.strip() or "1"),
            )

            final_state: dict[str, Any] = dict(state)
            token_count = 0

            for event in stream_story_events(state):
                event_type = event.get("event", "")

                if event_type == "token":
                    text = str(event.get("text", ""))
                    token_count += max(len(text.split()), 1)
                    token_stream.value += text
                    if token_count % 12 == 0:
                        page.update()
                    continue

                if event_type == "node_update":
                    node = event.get("node", "")
                    data = event.get("data", {})
                    if isinstance(data, dict):
                        final_state.update(data)
                    keys = ", ".join(event.get("keys", []))
                    add_event_line(f"[node_update] {node} | keys: {keys}", "#1b365d")
                    continue

                if event_type == "node_log":
                    add_event_line(f"[node_log] {event.get('message', '')}", "#6a4a00")
                    continue

                if event_type == "error":
                    add_event_line(f"[error] {event.get('message', '')}", "#a21515")
                    raise RuntimeError(str(event.get("message", "Unknown stream error")))

                if event_type == "done":
                    add_event_line("[done] stream completed", "#0f7a2a")

            final_story.value = str(final_state.get("final_story", ""))
            quality_report.value = str(final_state.get("quality_report", ""))
            final_state_holder.clear()
            final_state_holder.update(final_state)
            run_meta_text.value = (
                "Run: run_id="
                + str(final_state.get("run_id", "n/a"))
                + " | db="
                + str(final_state.get("sqlite_db_path", "n/a"))
                + " | log="
                + str(final_state.get("log_file_path", "n/a"))
            )
            status_text.value = "Completed"
            status_text.color = "#0f7a2a"
            add_event_line(
                "[summary] final_story=" + _compact_preview(final_state.get("final_story", "")),
                "#333",
            )
            render_history()

        except Exception as exc:
            status_text.value = f"Failed: {exc}"
            status_text.color = "#a21515"
            add_event_line(f"[exception] {exc}", "#a21515")
        finally:
            run_button.disabled = False
            page.update()

    def on_run(_: ft.ControlEvent) -> None:
        thread = threading.Thread(target=run_worker, daemon=True)
        thread.start()

    run_button.on_click = on_run
    check_button.on_click = handle_health
    export_button.on_click = handle_export

    add_profile_button = ft.OutlinedButton("Add/Update Profile", on_click=handle_add_profile)
    delete_profile_button = ft.OutlinedButton("Delete Profile", on_click=handle_delete_profile)
    add_memory_button = ft.OutlinedButton("Add/Update Memory", on_click=handle_add_memory)
    delete_memory_button = ft.OutlinedButton("Delete Memory", on_click=handle_delete_memory)
    delete_all_memory_button = ft.OutlinedButton("Delete All Memories", on_click=handle_delete_all_memories)
    refresh_history_button = ft.OutlinedButton("Refresh History", on_click=lambda _: render_history())
    refresh_roles_button = ft.OutlinedButton("Refresh Roles", on_click=lambda _: render_roles())

    form_row_1 = ft.Row([story_id, style, max_retry], wrap=True)
    form_row_2 = ft.Row([topic], wrap=True)
    form_row_3 = ft.Row([roles], wrap=True)
    action_row = ft.Row([run_button, check_button, export_button, status_text], alignment=ft.MainAxisAlignment.START)

    left_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text("Input", size=18, weight=ft.FontWeight.W_600),
                form_row_1,
                form_row_2,
                form_row_3,
                action_row,
                health_text,
                run_meta_text,
                ui_status_text,
                ft.Divider(),
                ft.Text("Event Stream", size=16, weight=ft.FontWeight.W_600),
                ft.Container(content=event_log, border=ft.border.all(1, "#d7dce5"), padding=8, border_radius=10, expand=True),
            ],
            expand=True,
            spacing=12,
        ),
        padding=14,
        border_radius=14,
        bgcolor="#ffffff",
        border=ft.border.all(1, "#dfe4ed"),
        expand=2,
    )

    output_tab = ft.Container(
        content=ft.Column(
            [token_stream, quality_report, final_story],
            expand=True,
            spacing=12,
        ),
        expand=True,
    )

    history_tab = ft.Container(
        content=ft.Column(
            [
                ft.Row([history_limit, refresh_history_button], wrap=True),
                selected_run_text,
                ft.Container(content=history_log, border=ft.border.all(1, "#d7dce5"), padding=8, border_radius=10, expand=True),
            ],
            spacing=12,
            expand=True,
        ),
        expand=True,
    )

    roles_tab = ft.Container(
        content=ft.Column(
            [
                ft.Row([role_id_input, memory_story_id_input, refresh_roles_button], wrap=True),
                profile_input,
                memory_text_input,
                ft.Row([add_profile_button, delete_profile_button], wrap=True),
                ft.Row([add_memory_button, delete_memory_button, delete_all_memory_button], wrap=True),
                ft.Text("Roles", size=16, weight=ft.FontWeight.W_600),
                ft.Container(content=role_list, border=ft.border.all(1, "#d7dce5"), padding=8, border_radius=10, expand=True),
            ],
            spacing=10,
            expand=True,
        ),
        expand=True,
    )

    right_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text("Workspace", size=18, weight=ft.FontWeight.W_600),
                ft.Tabs(
                    expand=True,
                    selected_index=0,
                    tabs=[
                        ft.Tab(text="Output", content=output_tab),
                        ft.Tab(text="History", content=history_tab),
                        ft.Tab(text="Roles", content=roles_tab),
                    ],
                ),
            ],
            expand=True,
            spacing=12,
        ),
        padding=14,
        border_radius=14,
        bgcolor="#ffffff",
        border=ft.border.all(1, "#dfe4ed"),
        expand=3,
    )

    page.add(
        ft.Column(
            [
                ft.Text("A Story Teller UI", size=26, weight=ft.FontWeight.W_700, color="#1e2a3a"),
                ft.Text("Flet prototype with node logs + token stream events", color="#49566a"),
                ft.Row([left_panel, right_panel], expand=True),
            ],
            expand=True,
        )
    )

    render_history()
    render_roles()


if __name__ == "__main__":
    ft.app(target=main)
