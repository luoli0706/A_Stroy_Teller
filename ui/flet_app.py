import json
import threading
from typing import Any

import flet as ft

from app.llm_client import get_story_client
from app.runtime import build_input_state, stream_story_events


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

    event_log = ft.ListView(expand=True, spacing=6, auto_scroll=True)
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

    def add_event_line(text: str, color: str = "#222") -> None:
        event_log.controls.append(ft.Text(text, size=12, color=color, selectable=True))
        page.update()

    def handle_health(_: ft.ControlEvent) -> None:
        result = get_story_client().health_check()
        health_text.value = f"Health: {'OK' if result.ok else 'FAILED'} | {result.message}"
        health_text.color = "#0f7a2a" if result.ok else "#a21515"
        page.update()

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

    form_row_1 = ft.Row([story_id, style, max_retry], wrap=True)
    form_row_2 = ft.Row([topic], wrap=True)
    form_row_3 = ft.Row([roles], wrap=True)
    action_row = ft.Row([run_button, check_button, status_text], alignment=ft.MainAxisAlignment.START)

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

    right_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text("Outputs", size=18, weight=ft.FontWeight.W_600),
                token_stream,
                quality_report,
                final_story,
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


if __name__ == "__main__":
    ft.app(target=main)
