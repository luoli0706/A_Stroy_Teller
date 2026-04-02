import json
import asyncio
import os
from pathlib import Path
import sys
from typing import Any

import flet as ft

# 确保 app 模块可导入
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import (
    DEFAULT_LANG, MODEL_PLANNER, MODEL_ROLE, MODEL_INTEGRATOR,
    MODEL_QUALITY, MODEL_EMBEDDING, RAG_ENABLED, RAG_TOP_K
)
from app.runtime import build_input_state, stream_story_events_async
from UI.components.log_viewer import LogViewer
from UI.components.story_panel import StoryControlPanel

# --- I18N ---
STRINGS = {
    "zh": {
        "app_title": "A Story Teller - v0.2.4 (Persistence Update)",
        "status_idle": "等待开始...",
        "status_running": "流程执行中 (支持断点续写)...",
        "status_done": "故事生成成功",
        "btn_run": "开始生成 (含持久化快照)",
    },
    "en": {
        "app_title": "A Story Teller - v0.2.4 (Persistence Update)",
        "status_idle": "Idle",
        "status_running": "Executing (Checkpoint Enabled)...",
        "status_done": "Story Generation Successful",
        "btn_run": "Run with Persistence",
    }
}

async def main(page: ft.Page):
    page.title = STRINGS[DEFAULT_LANG]["app_title"]
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    
    lang = DEFAULT_LANG
    def tr(key): return STRINGS[lang].get(key, key)

    # --- 初始化组件 ---
    log_viewer = LogViewer(hint_text="使用相同 Thread ID 再次运行，系统将自动从中断处恢复。")
    output_display = ft.TextField(
        label="最终成文与角色设定 (Story & Identities)", 
        multiline=True, 
        min_lines=20, 
        read_only=True, 
        expand=True,
        bgcolor="#fdfdfd",
        text_size=14
    )

    async def on_run_click(e):
        values = story_panel.get_values()
        thread_id = values["thread_id"]
        
        story_panel.set_status(tr("status_running"), color="orange")
        story_panel.set_busy(True)
        log_viewer.reset()
        log_viewer.clear_hint()
        output_display.value = ""
        page.update()

        state = build_input_state(
            story_id=values["story_id"],
            topic=values["topic"],
            style=values["style"],
            roles=values["roles"],
            max_retry=1
        )

        final_story_identities = ""

        try:
            # [v0.2.4] 传入 thread_id 启用断点续写
            async for event in stream_story_events_async(state, thread_id=thread_id):
                etype = event.get("event")
                if etype == "token":
                    output_display.value += event.get("text", "")
                    page.update()
                elif etype == "node_update":
                    node = event.get("node")
                    data = event.get("data", {})
                    log_viewer.add_log(f"✅ Node [{node}] saved to checkpoint", color="green")
                    
                    if node == "adapt_roles_to_framework":
                        identities = data.get("role_story_identities", {})
                        id_text = "\n--- 角色扮演分配 ---\n"
                        for rid, info in identities.items():
                            id_text += f"演员 [{rid}] 身份已确定\n"
                        final_story_identities = id_text
                elif etype == "error":
                    log_viewer.add_log(f"❌ 错误: {event.get('message')}", color="red")
            
            output_display.value = final_story_identities + "\n--- 正文 ---\n" + output_display.value
            story_panel.set_status(tr("status_done"), color="green")
        except Exception as ex:
            story_panel.set_status(f"Error: {str(ex)}", color="red")
        finally:
            story_panel.set_busy(False)
            page.update()

    story_panel = StoryControlPanel(on_run_click=on_run_click, tr=tr)

    page.add(
        ft.AppBar(
            title=ft.Text(tr("app_title"), weight="bold", color="white"), 
            bgcolor=ft.colors.BLUE_GREY_800,
            center_title=False
        ),
        ft.Row([
            ft.Column([
                story_panel.build(),
                ft.Divider(),
                ft.Text("系统日志与断点状态", size=16, weight="w600"),
                log_viewer,
            ], width=450, spacing=15),
            ft.VerticalDivider(width=1),
            ft.Column([
                ft.Text("故事输出 (支持 Markdown)", size=16, weight="w600"),
                output_display
            ], expand=True, spacing=15)
        ], expand=True)
    )

if __name__ == "__main__":
    ft.app(target=main)
