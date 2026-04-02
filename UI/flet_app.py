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
        "app_title": "A Story Teller - Alpha 0.2",
        "status_idle": "空闲",
        "status_running": "正在生成 (并行加速)...",
        "status_done": "生成成功",
        "btn_run": "并行生成故事",
    },
    "en": {
        "app_title": "A Story Teller - Alpha 0.2",
        "status_idle": "Idle",
        "status_running": "Generating (Parallel Optimized)...",
        "status_done": "Done",
        "btn_run": "Parallel Generate",
    }
}

async def main(page: ft.Page):
    page.title = STRINGS[DEFAULT_LANG]["app_title"]
    page.theme_mode = ft.ThemeMode.LIGHT
    
    lang = DEFAULT_LANG
    def tr(key): return STRINGS[lang].get(key, key)

    # --- 初始化组件 ---
    log_viewer = LogViewer(hint_text="暂无日志。点击生成后将实时显示节点状态。")
    output_display = ft.TextField(
        label="最终故事 (Final Story)", 
        multiline=True, 
        min_lines=15, 
        read_only=True, 
        expand=True,
        bgcolor="#fdfdfd"
    )

    async def on_run_click(e):
        values = story_panel.get_values()
        story_panel.set_status(tr("status_running"), color="orange")
        story_panel.set_busy(True)
        log_viewer.reset()
        log_viewer.clear_hint()
        output_display.value = ""
        page.update()

        state = build_input_state(
            story_id="alpha_02_test",
            topic=values["topic"],
            style=values["style"],
            roles=values["roles"],
            max_retry=1
        )

        try:
            async for event in stream_story_events_async(state):
                etype = event.get("event")
                if etype == "token":
                    output_display.value += event.get("text", "")
                    page.update()
                elif etype == "node_update":
                    node = event.get("node")
                    log_viewer.add_log(f"✅ Node Finished: {node}", color="green")
                elif etype == "error":
                    log_viewer.add_log(f"❌ Error: {event.get('message')}", color="red")
            
            story_panel.set_status(tr("status_done"), color="green")
        except Exception as ex:
            story_panel.set_status(f"Error: {str(ex)}", color="red")
        finally:
            story_panel.set_busy(False)
            page.update()

    story_panel = StoryControlPanel(on_run_click=on_run_click, tr=tr)

    # --- 布局结构 ---
    page.add(
        ft.AppBar(
            title=ft.Text(tr("app_title"), weight="bold"), 
            bgcolor=ft.colors.SURFACE_VARIANT,
            center_title=True
        ),
        ft.Column([
            story_panel.build(),
            ft.Divider(),
            ft.Text("实时状态日志 (Log Viewer)", size=16, weight="w600"),
            log_viewer,
            ft.Divider(),
            ft.Text("输出结果 (Output Display)", size=16, weight="w600"),
            output_display
        ], expand=True, spacing=15, scroll=ft.ScrollMode.AUTO)
    )

if __name__ == "__main__":
    ft.app(target=main)
