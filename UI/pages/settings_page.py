import flet as ft


def build_settings_page(
    *,
    settings_header: ft.Control,
    settings_runtime_header: ft.Control,
    settings_models_header: ft.Control,
    settings_rag_header: ft.Control,
    settings_paths_header: ft.Control,
    language_dropdown: ft.Control,
    check_button: ft.Control,
    refresh_settings_button: ft.Control,
    apply_settings_button: ft.Control,
    save_settings_button: ft.Control,
    health_text: ft.Control,
    settings_base_url: ft.Control,
    settings_model_planner: ft.Control,
    settings_model_role: ft.Control,
    settings_model_integrator: ft.Control,
    settings_model_quality: ft.Control,
    settings_model_embedding: ft.Control,
    settings_rag_enabled: ft.Control,
    settings_rag_top_k: ft.Control,
    settings_rag_chroma_dir: ft.Control,
    settings_rag_collection: ft.Control,
    settings_log_dir: ft.Control,
    settings_opt_dir: ft.Control,
) -> ft.Container:
    return ft.Container(
        visible=False,
        expand=True,
        padding=14,
        border_radius=14,
        bgcolor="#ffffff",
        border=ft.Border.all(1, "#dfe4ed"),
        content=ft.Column(
            [
                settings_header,
                ft.Container(
                    border=ft.Border.all(1, "#d7dce5"),
                    border_radius=10,
                    padding=12,
                    bgcolor="#ffffff",
                    content=ft.Column(
                        [
                            settings_runtime_header,
                            ft.Row(
                                [
                                    language_dropdown,
                                    check_button,
                                    refresh_settings_button,
                                    apply_settings_button,
                                    save_settings_button,
                                ],
                                wrap=True,
                            ),
                            health_text,
                            settings_base_url,
                        ],
                        spacing=10,
                    ),
                ),
                ft.Container(
                    border=ft.Border.all(1, "#d7dce5"),
                    border_radius=10,
                    padding=12,
                    bgcolor="#ffffff",
                    content=ft.Column(
                        [
                            settings_models_header,
                            ft.Row([settings_model_planner, settings_model_role], wrap=True),
                            ft.Row([settings_model_integrator, settings_model_quality], wrap=True),
                            settings_model_embedding,
                        ],
                        spacing=10,
                    ),
                ),
                ft.Container(
                    border=ft.Border.all(1, "#d7dce5"),
                    border_radius=10,
                    padding=12,
                    bgcolor="#ffffff",
                    content=ft.Column(
                        [
                            settings_rag_header,
                            ft.Row([settings_rag_enabled, settings_rag_top_k], wrap=True),
                            settings_rag_chroma_dir,
                            settings_rag_collection,
                        ],
                        spacing=10,
                    ),
                ),
                ft.Container(
                    border=ft.Border.all(1, "#d7dce5"),
                    border_radius=10,
                    padding=12,
                    bgcolor="#ffffff",
                    content=ft.Column(
                        [
                            settings_paths_header,
                            settings_log_dir,
                            settings_opt_dir,
                        ],
                        spacing=10,
                    ),
                ),
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )
