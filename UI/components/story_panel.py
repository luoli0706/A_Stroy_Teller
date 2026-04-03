import flet as ft
from typing import Callable, Coroutine, Any

class StoryControlPanel(ft.Column):
    """故事输入与控制面板 (v0.2.4 持久化增强版)。"""
    def __init__(
        self, 
        on_run_click: Callable[..., Coroutine[Any, Any, None]],
        tr: Callable[[str], str]
    ):
        super().__init__(spacing=15)
        self.on_run_click = on_run_click
        self.tr = tr

        self.thread_id_input = ft.TextField(
            label="会话 ID (Thread ID)", 
            value="session_001", 
            width=200,
            hint_text="使用相同 ID 可恢复中断的进度"
        )
        self.story_id_input = ft.TextField(label="故事 ID (Story ID)", value="urban_detective", width=200)
        self.topic_input = ft.TextField(label="主题 (Topic)", value="一场午夜的图书馆探险", expand=True)
        self.style_input = ft.TextField(label="风格 (Style)", value="悬疑", width=200)
        self.roles_input = ft.TextField(label="角色 (Roles, 演员名)", value="Reshaely,VanlyShan,SolinXuan", expand=True)
        
        self.status_text = ft.Text(tr("status_idle"), color="blue")
        self.progress_ring = ft.ProgressRing(visible=False, width=16, height=16)
        
        self.run_button = ft.ElevatedButton(
            tr("btn_run"), 
            on_click=self.on_run_click, 
            icon="play_circle_filled_rounded" # 改用字符串形式，避开 AttributeError
        )

    def build(self):
        return ft.Column([
            ft.Text("故事生成控制", size=20, weight="bold"),
            ft.Row([self.thread_id_input, self.story_id_input, self.style_input]),
            self.topic_input,
            self.roles_input,
            ft.Row([self.run_button, self.progress_ring, self.status_text])
        ], spacing=15)

    def set_status(self, text: str, color: str = "blue"):
        self.status_text.value = text
        self.status_text.color = color
        if self.page:
            self.update()

    def set_busy(self, busy: bool):
        self.progress_ring.visible = busy
        self.run_button.disabled = busy
        if self.page:
            self.update()

    def get_values(self):
        return {
            "thread_id": self.thread_id_input.value,
            "story_id": self.story_id_input.value,
            "topic": self.topic_input.value,
            "style": self.style_input.value,
            "roles": [r.strip() for r in self.roles_input.value.split(",") if r.strip()]
        }
