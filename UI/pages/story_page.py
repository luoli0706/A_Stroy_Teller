import flet as ft


def build_story_page(
    *,
    story_input_header: ft.Control,
    story_framework_tab_button: ft.Control,
    story_generation_tab_button: ft.Control,
    story_route_hint_text: ft.Control,
    story_tab_host: ft.Control,
    run_meta_text: ft.Control,
    ui_status_text: ft.Control,
    event_stream_header: ft.Control,
    event_stream_log: ft.Control,
    outputs_header: ft.Control,
    token_stream: ft.Control,
    quality_report: ft.Control,
    final_story: ft.Control,
    history_header: ft.Control,
    history_limit: ft.Control,
    refresh_history_button: ft.Control,
    selected_run_text: ft.Control,
    history_log: ft.Control,
) -> ft.Container:
    return ft.Container(
        visible=True,
        expand=True,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            expand=2,
                            padding=14,
                            border_radius=14,
                            bgcolor="#ffffff",
                            border=ft.Border.all(1, "#dfe4ed"),
                            content=ft.Column(
                                [
                                    story_input_header,
                                    ft.Row([story_framework_tab_button, story_generation_tab_button], wrap=True),
                                    story_route_hint_text,
                                    story_tab_host,
                                    run_meta_text,
                                    ui_status_text,
                                    ft.Container(
                                        border=ft.Border.all(1, "#d7dce5"),
                                        border_radius=10,
                                        padding=10,
                                        bgcolor="#ffffff",
                                        content=ft.Column(
                                            [
                                                event_stream_header,
                                                ft.Container(
                                                    content=event_stream_log,
                                                    border=ft.Border.all(1, "#d7dce5"),
                                                    border_radius=8,
                                                    padding=8,
                                                    bgcolor="#ffffff",
                                                    height=96,
                                                ),
                                            ],
                                            spacing=8,
                                        ),
                                    ),
                                ],
                                spacing=12,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                        ),
                        ft.Container(
                            expand=3,
                            padding=14,
                            border_radius=14,
                            bgcolor="#ffffff",
                            border=ft.Border.all(1, "#dfe4ed"),
                            content=ft.Column(
                                [
                                    outputs_header,
                                    token_stream,
                                    quality_report,
                                    final_story,
                                    ft.Divider(),
                                    history_header,
                                    ft.Row([history_limit, refresh_history_button], wrap=True),
                                    selected_run_text,
                                    ft.Container(
                                        content=history_log,
                                        border=ft.Border.all(1, "#d7dce5"),
                                        padding=8,
                                        border_radius=10,
                                        height=180,
                                    ),
                                ],
                                expand=True,
                                spacing=12,
                            ),
                        ),
                    ],
                    expand=True,
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
