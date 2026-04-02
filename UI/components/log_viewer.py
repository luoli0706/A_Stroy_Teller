import flet as ft

class LogViewer(ft.Column):
    """用于显示实时节点日志与生成进度的组件。"""
    def __init__(self, hint_text: str = "暂无日志"):
        super().__init__(scroll=ft.ScrollMode.AUTO, height=200, spacing=4)
        self.hint_text = hint_text
        self.reset()

    def add_log(self, text: str, color: str = "black", size: int = 12):
        self.controls.append(ft.Text(text, size=size, color=color, selectable=True))
        self.update()

    def reset(self):
        self.controls.clear()
        self.controls.append(ft.Text(self.hint_text, size=11, color="#6a7486"))
        self.update()

    def clear_hint(self):
        if self.controls and isinstance(self.controls[0], ft.Text) and self.controls[0].value == self.hint_text:
            self.controls.clear()
            self.update()
