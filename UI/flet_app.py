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
from app.role_memory import discover_roles

# --- I18N 简化版本 (Alpha 0.1) ---
STRINGS = {
    "zh": {
        "app_title": "A Story Teller - Alpha 0.1",
        "status_idle": "空闲",
        "status_running": "正在生成 (并行加速)...",
        "status_done": "生成成功",
        "btn_run": "并行生成故事",
        "tab_story": "生成故事",
        "tab_settings": "配置中心",
    },
    "en": {
        "app_title": "A Story Teller - Alpha 0.1",
        "status_idle": "Idle",
        "status_running": "Generating (Parallel Optimized)...",
        "status_done": "Done",
        "btn_run": "Parallel Generate",
        "tab_story": "Story",
        "tab_settings": "Settings",
    }
}

async def main(page: ft.Page):
    page.title = STRINGS[DEFAULT_LANG]["app_title"]
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # --- 状态变量 ---
    lang = DEFAULT_LANG
    def tr(key): return STRINGS[lang].get(key, key)

    # --- UI 组件 ---
    topic_input = ft.TextField(label="主题 (Topic)", value="一场午夜的图书馆探险", expand=True)
    style_input = ft.TextField(label="风格 (Style)", value="悬疑", width=200)
    roles_input = ft.TextField(label="角色 (Roles, 逗号分隔)", value="Reshaely,VanlyShan", expand=True)
    
    output_text = ft.TextField(label="输出内容", multiline=True, min_lines=15, read_only=True, expand=True)
    log_column = ft.Column(scroll=ft.ScrollMode.AUTO, height=200)
    status_text = ft.Text(tr("status_idle"), color="blue")
    
    progress_ring = ft.ProgressRing(visible=False, width=16, height=16)

    async def run_generation(e):
        status_text.value = tr("status_running")
        progress_ring.visible = True
        output_text.value = ""
        log_column.controls.clear()
        page.update()

        roles = [r.strip() for r in roles_input.value.split(",") if r.strip()]
        state = build_input_state(
            story_id="alpha_01_test",
            topic=topic_input.value,
            style=style_input.value,
            roles=roles,
            max_retry=1
        )

        try:
            async for event in stream_story_events_async(state):
                etype = event.get("event")
                if etype == "token":
                    output_text.value += event.get("text", "")
                elif etype == "node_update":
                    node = event.get("node")
                    log_column.controls.append(ft.Text(f"✅ Node Finished: {node}", size=12, color="green"))
                elif etype == "error":
                    log_column.controls.append(ft.Text(f"❌ Error: {event.get('message')}", color="red"))
                
                page.update()
            
            status_text.value = tr("status_done")
        except Exception as ex:
            status_text.value = f"Error: {str(ex)}"
        finally:
            progress_ring.visible = False
            page.update()

    # --- 布局 ---
    input_row = ft.Row([topic_input, style_input])
    action_row = ft.Row([
        ft.ElevatedButton(tr("btn_run"), on_click=run_generation, icon=ft.icons.PLAY_ARROW),
        progress_ring,
        status_text
    ])

    page.add(
        ft.AppBar(title=ft.Text(tr("app_title")), bgcolor=ft.colors.SURFACE_VARIANT),
        ft.Column([
            ft.Text("故事输入", size=20, weight="bold"),
            input_row,
            roles_input,
            action_row,
            ft.Divider(),
            ft.Text("实时日志", size=16),
            log_column,
            ft.Divider(),
            output_text
        ], expand=True, spacing=15)
    )

if __name__ == "__main__":
    # Flet 对异步的支持
    ft.app(target=main)
