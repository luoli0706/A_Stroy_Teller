import flet as ft
from typing import Callable, Coroutine, Any, List, Dict

class HistoryPanel(ft.Column):
    """[v0.2.5] 历史快照侧边栏组件。"""
    def __init__(
        self, 
        on_snapshot_click: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]
    ):
        super().__init__(width=300, spacing=10, scroll=ft.ScrollMode.AUTO)
        self.on_snapshot_click = on_snapshot_click
        self.snapshots_list = ft.ListView(expand=True, spacing=5)
        
        self.controls = [
            ft.Text("历史快照 (Checkpoints)", size=16, weight="bold"),
            ft.Divider(height=1),
            self.snapshots_list
        ]

    async def update_history(self, history: List[Dict[str, Any]]):
        """更新并渲染历史快照列表。"""
        self.snapshots_list.controls.clear()
        
        if not history:
            self.snapshots_list.controls.append(ft.Text("暂无历史记录", size=12, color="grey"))
        else:
            for idx, item in enumerate(history):
                # 提取元数据信息
                node_name = item.get("metadata", {}).get("source", "unknown")
                created_at = item.get("created_at", "N/A")
                
                # 创建点击条目
                tile = ft.ListTile(
                    title=ft.Text(f"Step {len(history)-idx}: {node_name}", size=13, weight="w500"),
                    subtitle=ft.Text(f"{created_at}", size=11),
                    on_click=lambda e, data=item: self.on_snapshot_click(data),
                    hover_color=ft.colors.BLACK12,
                    dense=True
                )
                self.snapshots_list.controls.append(tile)
        
        self.update()
