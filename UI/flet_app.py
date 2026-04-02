import json
import asyncio
import os
from pathlib import Path
import sys
from typing import Any, Dict

import flet as ft

# 确保 app 模块可导入
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import (
    DEFAULT_LANG, MODEL_PLANNER, MODEL_ROLE, MODEL_INTEGRATOR,
    MODEL_QUALITY, MODEL_EMBEDDING, RAG_ENABLED, RAG_TOP_K
)
from app.runtime import build_input_state, stream_story_events_async, get_thread_history_async
from UI.components.log_viewer import LogViewer
from UI.components.story_panel import StoryControlPanel
from UI.components.history_panel import HistoryPanel

# --- I18N ---
STRINGS = {
    "zh": {
        "app_title": "A Story Teller - v0.2.5 (Checkpoint Visualizer)",
        "status_idle": "等待开始...",
        "status_running": "流程执行中...",
        "status_done": "故事生成成功",
        "btn_run": "开始生成/恢复",
        "btn_refresh_history": "刷新历史记录",
    },
    "en": {
        "app_title": "A Story Teller - v0.2.5 (Checkpoint Visualizer)",
        "status_idle": "Idle",
        "status_running": "Executing Flow...",
        "status_done": "Success",
        "btn_run": "Run / Resume",
        "btn_refresh_history": "Refresh History",
    }
}

async def main(page: ft.Page):
    page.title = STRINGS[DEFAULT_LANG]["app_title"]
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0 # 使用内部 Container 控制 padding
    page.bgcolor = "#f4f7f9"
    
    lang = DEFAULT_LANG
    def tr(key): return STRINGS[lang].get(key, key)

    # --- 核心状态 ---
    current_history_data = []

    # --- 初始化组件 ---
    log_viewer = LogViewer(hint_text="执行详情将在此显示...")
    
    output_display = ft.Markdown(
        value="## 故事预览区域\n请在左侧点击历史快照或开始新的生成任务。",
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        expand=True,
    )
    
    output_container = ft.Container(
        content=ft.Column([output_display], scroll=ft.ScrollMode.AUTO),
        bgcolor="white",
        padding=20,
        border_radius=10,
        expand=True,
        border=ft.border.all(1, "#e0e0e0")
    )

    async def on_snapshot_click(snapshot_data: Dict[str, Any]):
        """当点击历史快照时触发。"""
        values = snapshot_data.get("values", {})
        story_content = values.get("integrated_draft") or values.get("final_story") or ""
        
        # 构造预览 Markdown
        topic = values.get("topic", "未命名故事")
        outline = values.get("global_outline", "尚未生成大纲")
        
        md_text = f"# {topic}\n\n"
        
        if story_content:
            md_text += f"## 整合正文\n\n{story_content}\n\n"
        
        md_text += f"## 全局大纲\n\n{outline}\n\n"
        
        if "role_story_identities" in values:
            md_text += "## 角色扮演分配\n"
            for rid, identity in values["role_story_identities"].items():
                name = identity.get("story_name", rid)
                goal = identity.get("story_specific_goal", "N/A")
                md_text += f"- **{rid}** 扮演 **{name}**: {goal}\n"

        output_display.value = md_text
        page.update()

    history_panel = HistoryPanel(on_snapshot_click=on_snapshot_click)

    async def refresh_history():
        thread_id = story_panel.thread_id_input.value
        history = await get_thread_history_async(thread_id)
        await history_panel.update_history(history)

    async def on_run_click(e):
        values = story_panel.get_values()
        thread_id = values["thread_id"]
        
        story_panel.set_status(tr("status_running"), color="orange")
        story_panel.set_busy(True)
        log_viewer.reset()
        output_display.value = "## 正在生成中...\n查看左侧日志了解进度。"
        page.update()

        state = build_input_state(
            story_id=values["story_id"],
            topic=values["topic"],
            style=values["style"],
            roles=values["roles"],
            max_retry=1
        )

        try:
            async for event in stream_story_events_async(state, thread_id=thread_id):
                etype = event.get("event")
                if etype == "node_update":
                    node = event.get("node")
                    log_viewer.add_log(f"✅ Node [{node}] completed & checkpointed", color="green")
                    # 每次节点完成都刷新历史
                    await refresh_history()
                elif etype == "error":
                    log_viewer.add_log(f"❌ Error: {event.get('message')}", color="red")
            
            story_panel.set_status(tr("status_done"), color="green")
        except Exception as ex:
            story_panel.set_status(f"Error: {str(ex)}", color="red")
        finally:
            story_panel.set_busy(False)
            await refresh_history()
            page.update()

    story_panel = StoryControlPanel(on_run_click=on_run_click, tr=tr)

    # --- 顶栏 ---
    app_bar = ft.AppBar(
        leading=ft.Icon(ft.icons.AUTO_STORIES, color="white"),
        title=ft.Text(tr("app_title"), weight="bold", color="white"),
        bgcolor=ft.colors.BLUE_GREY_900,
        center_title=False,
        actions=[
            ft.IconButton(ft.icons.REFRESH, on_click=lambda _: refresh_history(), tooltip=tr("btn_refresh_history"), icon_color="white")
        ]
    )

    # --- 整体布局 ---
    main_layout = ft.Row(
        [
            # 左侧：控制与日志
            ft.Container(
                content=ft.Column([
                    story_panel.build(),
                    ft.Divider(),
                    ft.Text("实时状态日志", size=14, weight="w600"),
                    log_viewer,
                ], scroll=ft.ScrollMode.AUTO),
                width=400,
                padding=20,
                bgcolor="white",
                border_radius=10,
                border=ft.border.all(1, "#e0e0e0")
            ),
            # 中间：历史快照
            ft.Container(
                content=history_panel,
                width=280,
                padding=15,
                bgcolor="white",
                border_radius=10,
                border=ft.border.all(1, "#e0e0e0")
            ),
            # 右侧：预览区
            output_container
        ],
        expand=True,
        spacing=15
    )

    page.add(
        app_bar,
        ft.Container(main_layout, padding=20, expand=True)
    )
    
    # 初始刷新历史
    await refresh_history()

if __name__ == "__main__":
    ft.app(target=main)
