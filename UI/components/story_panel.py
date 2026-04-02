import flet as ft
from typing import Callable, Coroutine, Any

class StoryControlPanel(ft.Column):
    """故事输入与控制面板。"""
    def __init__(
        self, 
        on_run_click: Callable[..., Coroutine[Any, Any, None]],
        tr: Callable[[str], str]
    ):
        super().__init__(spacing=15)
        self.on_run_click = on_run_click
        self.tr = tr

        self.topic_input = ft.TextField(label="主题 (Topic)", value="一场午夜的图书馆探险", expand=True)
        self.style_input = ft.TextField(label="风格 (Style)", value="悬疑", width=200)
        self.roles_input = ft.TextField(label="角色 (Roles, 逗号分隔)", value="Reshaely,VanlyShan", expand=True)
        
        self.status_text = ft.Text(tr("status_idle"), color="blue")
        self.progress_ring = ft.ProgressRing(visible=False, width=16, height=16)
        
        self.run_button = ft.ElevatedButton(
            tr("btn_run"), 
            on_click=self.on_run_click, 
            icon=ft.icons.PLAY_ARROW
        )

    def build(self):
        return ft.Column([
            ft.Text("故事输入", size=20, weight="bold"),
            ft.Row([self.topic_input, self.style_input]),
            self.roles_input,
            ft.Row([self.run_button, self.progress_ring, self.status_text])
        ], spacing=15)

    def set_status(self, text: str, color: str = "blue"):
        self.status_text.value = text
        self.status_text.color = color
        self.update()

    def set_busy(self, busy: bool):
        self.progress_ring.visible = busy
        self.run_button.disabled = busy
        self.update()

    def get_values(self):
        return {
            "topic": self.topic_input.value,
            "style": self.style_input.value,
            "roles": [r.strip() for r in self.roles_input.value.split(",") if r.strip()]
        }
