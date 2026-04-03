import flet as ft

class LogViewer(ft.Column):
    """用于显示实时节点日志与生成进度的组件。"""
    def __init__(self, hint_text: str = "暂无日志"):
        super().__init__(scroll=ft.ScrollMode.AUTO, height=200, spacing=4)
        self.hint_text = hint_text
        # 初始化时不调用 update
        self.reset(do_update=False)

    def add_log(self, text: str, color: str = "black", size: int = 12):
        self.controls.append(ft.Text(text, size=size, color=color, selectable=True))
        if self.page:
            self.update()

    def reset(self, do_update: bool = True):
        self.controls.clear()
        self.controls.append(ft.Text(self.hint_text, size=11, color="#6a7486"))
        if do_update and self.page:
            self.update()

    def clear_hint(self):
        if self.controls and isinstance(self.controls[0], ft.Text) and self.controls[0].value == self.hint_text:
            self.controls.clear()
            if self.page:
                self.update()
