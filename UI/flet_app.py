import json
import threading
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

import flet as ft


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm_client import get_story_client
from app.role_memory import (
    add_role_memory_slice,
    add_role_profile,
    delete_all_role_memories,
    delete_role_memory_slice,
    delete_role_profile,
    discover_roles,
)
from app.runtime import build_input_state, stream_story_events
from app.story_framework import load_story_framework
from app.sqlite_store import get_story_run, list_story_runs


I18N = {
    "zh": {
        "app_title": "A Story Teller UI",
        "app_subtitle": "支持路由切换、日志与 token 流事件的 Flet 客户端",
        "nav_story": "故事管理",
        "nav_role": "角色管理",
        "nav_settings": "设置",
        "story_input": "故事输入",
        "story_id": "故事框架 ID",
        "story_tab_framework": "故事框架",
        "story_tab_generation": "故事生成",
        "story_route_hint": "当前路由: 页={page} | 故事标签={story_tab} | 生成子标签={generation_tab}",
        "framework_id": "框架查询 ID",
        "framework_preview": "框架内容预览",
        "query_framework": "查询框架",
        "refresh_frameworks": "刷新框架列表",
        "framework_load": "加载框架",
        "frameworks_header": "可用框架",
        "framework_resolved": "当前加载框架: {story_id}",
        "framework_resolved_none": "当前加载框架: 无",
        "story_framework_guide": "步骤: 1) 输入框架ID并查询或从列表加载；2) 确认\"当前加载框架\"。",
        "framework_query_required": "请输入框架 ID。",
        "framework_loaded": "已加载框架: {story_id}",
        "no_frameworks": "暂无可用框架。",
        "topic": "主题",
        "style": "风格",
        "roles": "角色（逗号分隔）",
        "story_mode": "生成模式",
        "generation_subtabs": "故事生成子标签",
        "generation_single_panel": "单角色生成面板",
        "generation_multi_panel": "多角色生成面板",
        "story_mode_single": "生成模式: 单角色",
        "story_mode_multi": "生成模式: 多角色",
        "story_role_name": "生成角色名字（英文）",
        "story_role_pool": "角色加载池",
        "generation_tab_single": "单角色生成",
        "generation_tab_multi": "多角色生成",
        "selected_story_role": "当前单角色: {role_id}",
        "selected_story_role_none": "当前单角色: 无",
        "load_role_for_story": "加载角色到生成器",
        "load_all_roles_for_story": "加载全部角色",
        "generate_single_story": "生成单角色故事",
        "generate_multi_story": "生成多角色故事",
        "story_role_required": "请先选择或输入单角色。",
        "story_roles_required": "请先加载或填写多角色列表。",
        "story_role_loaded": "已加载生成角色: {role_id}",
        "story_roles_loaded": "已加载全部角色: {count}",
        "story_memory_saved": "单角色故事已写入记忆: {role_id}/{story_id}",
        "story_memory_save_failed": "写入角色记忆失败: {message}",
        "story_generation_guide": "步骤: 1) 先加载角色；2) 选择单角色或多角色子标签；3) 点击对应生成按钮。",
        "max_retry": "最大重试",
        "run_story": "运行故事",
        "export_opt": "导出到 opt",
        "status_idle": "空闲",
        "status_running": "运行中...",
        "status_completed": "完成",
        "status_failed": "失败: {error}",
        "health_not_checked": "健康检查：未执行",
        "ui_ready": "UI 已就绪",
        "run_meta_init": "运行: -",
        "event_stream": "事件流",
        "show_event_stream": "显示事件流",
        "hide_event_stream": "隐藏事件流",
        "event_stream_hint": "暂无事件。点击生成后将实时显示节点日志与 token。",
        "outputs": "输出",
        "token_stream": "Token 流",
        "quality_report": "质量报告",
        "final_story": "最终故事",
        "history": "历史记录",
        "history_limit": "历史条数",
        "refresh_history": "刷新历史",
        "selected_run_none": "已选运行: 无",
        "role_management": "角色管理",
        "role_id": "角色 ID",
        "role_profile": "角色设定",
        "role_name": "角色名字（英文）",
        "memory_story_id": "记忆故事 ID",
        "memory_slice_text": "记忆切片内容",
        "role_query_profile": "查询角色设定",
        "role_load_by_name": "按名字加载",
        "role_load": "一键加载",
        "memory_slices": "记忆切片子标签",
        "no_memory_slices": "当前角色暂无记忆切片。",
        "active_memory_slice": "当前切片: {story_id}",
        "active_memory_slice_none": "当前切片: 无",
        "add_update_profile": "新增/更新设定",
        "delete_profile": "删除设定",
        "add_update_memory": "新增/更新记忆",
        "delete_memory": "删除记忆",
        "delete_all_memories": "删除全部记忆",
        "refresh_roles": "刷新角色",
        "roles_header": "角色列表",
        "settings": "设置",
        "check_health": "健康检查",
        "refresh_settings": "刷新设置",
        "language": "语言",
        "setting_base_url": "OLLAMA_BASE_URL",
        "setting_model_planner": "规划模型",
        "setting_model_role": "角色模型",
        "setting_model_integrator": "整合模型",
        "setting_model_quality": "质检模型",
        "setting_log_dir": "日志目录",
        "setting_opt_dir": "导出目录",
        "health_ok": "健康检查：正常 | {message}",
        "health_failed": "健康检查：失败 | {message}",
        "no_story_runs": "暂无故事运行记录。",
        "no_roles": "暂无角色。",
        "role_not_found": "未找到角色: {name}",
        "role_loaded": "已加载角色: {role_id}",
        "memory_slice_loaded": "已加载记忆切片: {role_id}/{story_id}",
        "run_not_found": "未找到运行记录 #{run_id}",
        "loaded_run": "已加载运行 #{run_id}",
        "quality_not_persisted": "来自历史加载：当前数据库结构未持久化 quality_report。",
        "selected_run": "已选运行: {run_id} | {created_at} | 风格={style}",
        "run_starting": "运行: 启动中",
        "run_meta": "运行: run_id={run_id} | db={db} | log={log}",
        "summary_final_story": "[摘要] 最终故事={preview}",
        "stream_done": "[完成] 流式执行结束",
        "stream_error": "[错误] {message}",
        "stream_exception": "[异常] {message}",
        "export_nothing": "暂无可导出内容，请先运行一次故事。",
        "exported": "导出完成: {md_path} 和 {json_path}",
        "role_id_required": "角色 ID 必填。",
        "role_story_required": "角色 ID 和记忆故事 ID 必填。",
        "profile_saved": "设定已保存: {path}",
        "profile_deleted": "设定删除={deleted}, 角色={role_id}",
        "memory_saved": "记忆已保存: {path}",
        "memory_deleted": "记忆删除={deleted}, {role_id}/{story_id}",
        "memory_all_deleted": "已删除记忆切片={count}, 角色={role_id}",
    },
    "en": {
        "app_title": "A Story Teller UI",
        "app_subtitle": "Flet client with route switching, logs, and token stream events",
        "nav_story": "Story",
        "nav_role": "Roles",
        "nav_settings": "Settings",
        "story_input": "Story Input",
        "story_id": "Story ID",
        "story_tab_framework": "Framework",
        "story_tab_generation": "Generation",
        "story_route_hint": "Route: page={page} | story tab={story_tab} | generation tab={generation_tab}",
        "framework_id": "Framework Query ID",
        "framework_preview": "Framework Preview",
        "query_framework": "Query Framework",
        "refresh_frameworks": "Refresh Frameworks",
        "framework_load": "Load Framework",
        "frameworks_header": "Available Frameworks",
        "framework_resolved": "Loaded Framework: {story_id}",
        "framework_resolved_none": "Loaded Framework: none",
        "story_framework_guide": "Steps: 1) Query by framework ID or load from list; 2) confirm the loaded framework.",
        "framework_query_required": "Please input a framework ID.",
        "framework_loaded": "Loaded framework: {story_id}",
        "no_frameworks": "No frameworks found.",
        "topic": "Topic",
        "style": "Style",
        "roles": "Roles (comma-separated)",
        "story_mode": "Generation Mode",
        "generation_subtabs": "Generation Sub-Tabs",
        "generation_single_panel": "Single-Role Generation Panel",
        "generation_multi_panel": "Multi-Role Generation Panel",
        "story_mode_single": "Mode: single role",
        "story_mode_multi": "Mode: multiple roles",
        "story_role_name": "Generator Role Name (EN)",
        "story_role_pool": "Role Loading Pool",
        "generation_tab_single": "Single-Role",
        "generation_tab_multi": "Multi-Role",
        "selected_story_role": "Current Single Role: {role_id}",
        "selected_story_role_none": "Current Single Role: none",
        "load_role_for_story": "Load Role To Generator",
        "load_all_roles_for_story": "Load All Roles",
        "generate_single_story": "Generate Single-Role Story",
        "generate_multi_story": "Generate Multi-Role Story",
        "story_role_required": "Select or input one role first.",
        "story_roles_required": "Load or input multiple roles first.",
        "story_role_loaded": "Loaded generator role: {role_id}",
        "story_roles_loaded": "Loaded all roles: {count}",
        "story_memory_saved": "Single-role story saved to memory: {role_id}/{story_id}",
        "story_memory_save_failed": "Failed to persist role memory: {message}",
        "story_generation_guide": "Steps: 1) Load roles first; 2) choose single-role or multi-role tab; 3) click generate.",
        "max_retry": "Max Retry",
        "run_story": "Run Story",
        "export_opt": "Export To opt",
        "status_idle": "Idle",
        "status_running": "Running...",
        "status_completed": "Completed",
        "status_failed": "Failed: {error}",
        "health_not_checked": "Health: not checked",
        "ui_ready": "UI ready",
        "run_meta_init": "Run: -",
        "event_stream": "Event Stream",
        "show_event_stream": "Show Event Stream",
        "hide_event_stream": "Hide Event Stream",
        "event_stream_hint": "No events yet. Start generation to see node logs and token stream here.",
        "outputs": "Outputs",
        "token_stream": "Token Stream",
        "quality_report": "Quality Report",
        "final_story": "Final Story",
        "history": "History",
        "history_limit": "History Limit",
        "refresh_history": "Refresh History",
        "selected_run_none": "Selected Run: none",
        "role_management": "Role Management",
        "role_id": "Role ID",
        "role_profile": "Role Profile",
        "role_name": "Role Name (EN)",
        "memory_story_id": "Memory Story ID",
        "memory_slice_text": "Memory Slice Text",
        "role_query_profile": "Query Profile",
        "role_load_by_name": "Load By Name",
        "role_load": "Load",
        "memory_slices": "Memory Slice Tabs",
        "no_memory_slices": "No memory slices for current role.",
        "active_memory_slice": "Active Slice: {story_id}",
        "active_memory_slice_none": "Active Slice: none",
        "add_update_profile": "Add/Update Profile",
        "delete_profile": "Delete Profile",
        "add_update_memory": "Add/Update Memory",
        "delete_memory": "Delete Memory",
        "delete_all_memories": "Delete All Memories",
        "refresh_roles": "Refresh Roles",
        "roles_header": "Roles",
        "settings": "Settings",
        "check_health": "Health Check",
        "refresh_settings": "Refresh Settings",
        "language": "Language",
        "setting_base_url": "OLLAMA_BASE_URL",
        "setting_model_planner": "Planner Model",
        "setting_model_role": "Role Model",
        "setting_model_integrator": "Integrator Model",
        "setting_model_quality": "Quality Model",
        "setting_log_dir": "Log Directory",
        "setting_opt_dir": "Export Directory",
        "health_ok": "Health: OK | {message}",
        "health_failed": "Health: FAILED | {message}",
        "no_story_runs": "No story runs found.",
        "no_roles": "No roles found.",
        "role_not_found": "Role not found: {name}",
        "role_loaded": "Loaded role: {role_id}",
        "memory_slice_loaded": "Loaded memory slice: {role_id}/{story_id}",
        "run_not_found": "Run #{run_id} not found.",
        "loaded_run": "Loaded run #{run_id}",
        "quality_not_persisted": "Loaded from history; quality_report is not persisted in current schema.",
        "selected_run": "Selected Run: {run_id} | {created_at} | style={style}",
        "run_starting": "Run: starting",
        "run_meta": "Run: run_id={run_id} | db={db} | log={log}",
        "summary_final_story": "[summary] final_story={preview}",
        "stream_done": "[done] stream completed",
        "stream_error": "[error] {message}",
        "stream_exception": "[exception] {message}",
        "export_nothing": "Nothing to export yet. Run a story first.",
        "exported": "Exported: {md_path} and {json_path}",
        "role_id_required": "Role ID is required.",
        "role_story_required": "Role ID and Memory Story ID are required.",
        "profile_saved": "Profile saved: {path}",
        "profile_deleted": "Profile deleted={deleted} for {role_id}",
        "memory_saved": "Memory saved: {path}",
        "memory_deleted": "Memory deleted={deleted} for {role_id}/{story_id}",
        "memory_all_deleted": "Deleted memory slices={count} for {role_id}",
    },
}


def _compact_preview(value: Any, max_len: int = 220) -> str:
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len] + " ..."


def main(page: ft.Page) -> None:
    current_lang = {"value": "zh"}

    def tr(key: str, **kwargs: Any) -> str:
        text = I18N[current_lang["value"]].get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    page.title = tr("app_title")
    page.window_width = 1240
    page.window_height = 860
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#f7f8fb"

    story_id = ft.TextField(label=tr("story_id"), value="urban_detective", width=220)
    topic = ft.TextField(label=tr("topic"), value="midnight archive theft", expand=True)
    style = ft.TextField(label=tr("style"), value="noir", width=180)
    roles = ft.TextField(
        label=tr("roles"),
        value="Reshaely,VanlyShan,SolinXuan",
        expand=True,
    )
    max_retry = ft.TextField(label=tr("max_retry"), value="1", width=120)

    status_text = ft.Text(tr("status_idle"), color="#444")
    health_text = ft.Text(tr("health_not_checked"), color="#555")
    run_meta_text = ft.Text(tr("run_meta_init"), selectable=True)
    ui_status_text = ft.Text(tr("ui_ready"), color="#555")

    event_stream_log = ft.Column(expand=True, spacing=4, scroll=ft.ScrollMode.AUTO)
    event_stream_hint_text = ft.Text(tr("event_stream_hint"), color="#6a7486", size=11)
    history_log = ft.ListView(expand=True, spacing=6, auto_scroll=True)
    role_list = ft.ListView(expand=True, spacing=6, auto_scroll=True)
    token_stream = ft.TextField(
        label=tr("token_stream"),
        multiline=True,
        min_lines=8,
        max_lines=18,
        read_only=True,
        value="",
    )
    final_story = ft.TextField(
        label=tr("final_story"),
        multiline=True,
        min_lines=12,
        max_lines=22,
        read_only=True,
        value="",
    )
    quality_report = ft.TextField(
        label=tr("quality_report"),
        multiline=True,
        min_lines=4,
        max_lines=8,
        read_only=True,
        value="",
    )

    run_single_button = ft.Button(tr("generate_single_story"))
    run_single_quick_button = ft.OutlinedButton(tr("generate_single_story"))
    run_multi_button = ft.Button(tr("generate_multi_story"))
    check_button = ft.OutlinedButton(tr("check_health"))
    export_button = ft.OutlinedButton(tr("export_opt"))

    story_framework_id_input = ft.TextField(label=tr("framework_id"), value=story_id.value, width=220)
    framework_preview_input = ft.TextField(
        label=tr("framework_preview"),
        multiline=True,
        min_lines=5,
        max_lines=6,
        read_only=True,
        value="",
        bgcolor="#ffffff",
    )
    framework_selector = ft.Dropdown(width=260, options=[])
    resolved_framework_id = {"value": ""}
    framework_resolved_text = ft.Text(tr("framework_resolved_none"), color="#555", selectable=True)

    story_selected_role = {"value": ""}
    story_generation_mode = {"value": "multi"}
    story_tab_state = {"value": "generation"}
    generation_tab_state = {"value": "multi"}
    page_state = {"value": "story"}
    story_role_name_input = ft.TextField(label=tr("story_role_name"), width=260)
    story_selected_role_text = ft.Text(tr("selected_story_role_none"), color="#555", selectable=True)
    story_role_selector = ft.Dropdown(width=260, options=[])
    story_route_hint_text = ft.Text("", color="#6a7486", size=11, selectable=True)

    role_id_input = ft.TextField(label=tr("role_id"), width=220)
    role_name_input = ft.TextField(label=tr("role_name"), width=240)
    profile_input = ft.TextField(label=tr("role_profile"), multiline=True, min_lines=5, max_lines=10)
    memory_story_id_input = ft.TextField(label=tr("memory_story_id"), width=220)
    memory_text_input = ft.TextField(label=tr("memory_slice_text"), multiline=True, min_lines=4, max_lines=8)
    active_memory_slice_text = ft.Text(tr("active_memory_slice_none"), color="#555", selectable=True)
    memory_slice_tabs = ft.Row(wrap=True, spacing=8)
    selected_memory_slice = {"value": ""}

    history_limit = ft.TextField(label=tr("history_limit"), value="20", width=120)
    selected_run_text = ft.Text(tr("selected_run_none"), selectable=True)

    final_state_holder: dict[str, Any] = {}

    nav_story_button = ft.OutlinedButton(tr("nav_story"))
    nav_role_button = ft.OutlinedButton(tr("nav_role"))
    nav_settings_button = ft.OutlinedButton(tr("nav_settings"))

    app_title_text = ft.Text(tr("app_title"), size=26, weight=ft.FontWeight.W_700, color="#1e2a3a")
    app_subtitle_text = ft.Text(tr("app_subtitle"), color="#49566a")
    story_input_header = ft.Text(tr("story_input"), size=18, weight=ft.FontWeight.W_600)
    event_stream_header = ft.Text(tr("event_stream"), size=16, weight=ft.FontWeight.W_600)
    outputs_header = ft.Text(tr("outputs"), size=18, weight=ft.FontWeight.W_600)
    history_header = ft.Text(tr("history"), size=16, weight=ft.FontWeight.W_600)
    role_header = ft.Text(tr("role_management"), size=18, weight=ft.FontWeight.W_600)
    roles_list_header = ft.Text(tr("roles_header"), size=16, weight=ft.FontWeight.W_600)
    settings_header = ft.Text(tr("settings"), size=18, weight=ft.FontWeight.W_600)

    def render_event_stream_hint() -> None:
        if not event_stream_log.controls:
            event_stream_log.controls.append(event_stream_hint_text)

    def add_event_line(text: str, color: str = "#222") -> None:
        if event_stream_log.controls and event_stream_log.controls[0] is event_stream_hint_text:
            event_stream_log.controls.clear()
        event_stream_log.controls.append(ft.Text(text, size=12, color=color, selectable=True))
        page.update()

    def set_ui_status(text: str, color: str = "#555") -> None:
        ui_status_text.value = text
        ui_status_text.color = color
        page.update()

    def render_history() -> None:
        history_log.controls.clear()
        try:
            limit = int(history_limit.value.strip() or "20")
        except ValueError:
            limit = 20

        runs = list_story_runs(limit=limit)
        if not runs:
            history_log.controls.append(ft.Text(tr("no_story_runs"), color="#666"))
            page.update()
            return

        for run in runs:
            run_id = int(run.get("id", 0))
            title = f"#{run_id} | {run.get('created_at', '')} | {run.get('topic', '')}"

            def load_run(_: ft.ControlEvent, selected_id: int = run_id) -> None:
                data = get_story_run(selected_id)
                if not data:
                    set_ui_status(tr("run_not_found", run_id=selected_id), "#a21515")
                    return
                final_story.value = str(data.get("final_story", ""))
                quality_report.value = tr("quality_not_persisted")
                selected_run_text.value = tr(
                    "selected_run",
                    run_id=selected_id,
                    created_at=data.get("created_at", ""),
                    style=data.get("style", ""),
                )
                set_ui_status(tr("loaded_run", run_id=selected_id), "#0f7a2a")
                page.update()

            history_log.controls.append(
                ft.Row(
                    [
                        ft.TextButton(content=title, on_click=load_run),
                        ft.Text(str(run.get("roles_json", "")), size=11, color="#5a6780"),
                    ],
                    wrap=True,
                )
            )
        page.update()

    def render_roles() -> None:
        role_list.controls.clear()
        role_ids = discover_roles("role")
        if not role_ids:
            role_list.controls.append(ft.Text(tr("no_roles"), color="#666"))
            page.update()
            return

        def quick_load(role_id: str) -> None:
            load_role_to_editor(role_id)

        for role_id in role_ids:
            role_list.controls.append(
                ft.Row(
                    [
                        ft.Text(role_id, selectable=True),
                        ft.TextButton(content=tr("role_load"), on_click=lambda _, rid=role_id: quick_load(rid)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )
        page.update()

    def _read_role_profile(role_id: str) -> str:
        profile_path = Path("role") / role_id / "profile.md"
        if not profile_path.exists():
            return ""
        return profile_path.read_text(encoding="utf-8").strip()

    def _list_role_memory_story_ids(role_id: str) -> list[str]:
        memory_path = Path("memory") / role_id
        if not memory_path.exists():
            return []
        return sorted(item.stem for item in memory_path.glob("*.md"))

    def _read_memory_slice(role_id: str, story_id: str) -> str:
        memory_file = Path("memory") / role_id / f"{story_id}.md"
        if not memory_file.exists():
            return ""
        return memory_file.read_text(encoding="utf-8").strip()

    def _find_role_id_by_name(role_name: str) -> str | None:
        normalized = role_name.strip().lower()
        if not normalized:
            return None
        role_ids = discover_roles("role")
        exact = [rid for rid in role_ids if rid.lower() == normalized]
        if exact:
            return exact[0]
        partial = [rid for rid in role_ids if normalized in rid.lower()]
        if partial:
            return partial[0]
        return None

    def _list_story_framework_ids() -> list[str]:
        stories_root = Path("stories")
        if not stories_root.exists():
            return []
        return sorted(
            child.name
            for child in stories_root.iterdir()
            if child.is_dir() and (child / "framework.md").exists()
        )

    def render_frameworks() -> None:
        framework_ids = _list_story_framework_ids()
        framework_selector.options = [ft.dropdown.Option(key=item, text=item) for item in framework_ids]
        if framework_ids and (framework_selector.value not in framework_ids):
            framework_selector.value = framework_ids[0]
        if not framework_ids:
            framework_selector.value = None
        page.update()

    def load_framework_to_editor(target_story_id: str, announce: bool = True) -> None:
        requested_id = target_story_id.strip()
        if not requested_id:
            set_ui_status(tr("framework_query_required"), "#a21515")
            return

        resolved_story_id, framework_text = load_story_framework(requested_id, "stories")
        story_framework_id_input.value = requested_id
        story_id.value = resolved_story_id
        framework_preview_input.value = framework_text
        resolved_framework_id["value"] = resolved_story_id
        framework_resolved_text.value = tr("framework_resolved", story_id=resolved_story_id)
        if announce:
            set_ui_status(tr("framework_loaded", story_id=resolved_story_id), "#0f7a2a")
        page.update()

    def handle_query_framework(_: ft.ControlEvent) -> None:
        load_framework_to_editor(story_framework_id_input.value)

    def handle_load_selected_framework(_: ft.ControlEvent) -> None:
        selected = (framework_selector.value or "").strip()
        if not selected:
            set_ui_status(tr("no_frameworks"), "#a21515")
            return
        load_framework_to_editor(selected)

    def handle_framework_selector(_: ft.ControlEvent) -> None:
        story_framework_id_input.value = (framework_selector.value or "").strip()
        page.update()

    def load_story_role_to_generator(role_id: str, announce: bool = True) -> None:
        story_selected_role["value"] = role_id
        story_role_name_input.value = role_id
        story_selected_role_text.value = tr("selected_story_role", role_id=role_id)

        current_roles = [item.strip() for item in roles.value.split(",") if item.strip()]
        if role_id not in current_roles:
            current_roles.append(role_id)
            roles.value = ",".join(current_roles)

        if announce:
            set_ui_status(tr("story_role_loaded", role_id=role_id), "#0f7a2a")
        page.update()

    def render_story_role_pool() -> None:
        role_ids = discover_roles("role")
        story_role_selector.options = [ft.dropdown.Option(key=item, text=item) for item in role_ids]
        if role_ids and (story_role_selector.value not in role_ids):
            story_role_selector.value = role_ids[0]
        if not role_ids:
            story_role_selector.value = None
        page.update()

    def handle_load_story_role_by_name(_: ft.ControlEvent) -> None:
        role_name = story_role_name_input.value.strip()
        role_id = _find_role_id_by_name(role_name)
        if not role_id:
            role_id = (story_role_selector.value or "").strip() or None
        if not role_id:
            set_ui_status(tr("role_not_found", name=role_name), "#a21515")
            return
        load_story_role_to_generator(role_id)
        render_story_role_pool()

    def handle_story_role_selector(_: ft.ControlEvent) -> None:
        selected = (story_role_selector.value or "").strip()
        if not selected:
            return
        load_story_role_to_generator(selected)
        render_story_role_pool()

    def handle_load_all_story_roles(_: ft.ControlEvent) -> None:
        role_ids = discover_roles("role")
        if not role_ids:
            set_ui_status(tr("no_roles"), "#a21515")
            return

        roles.value = ",".join(role_ids)
        if story_selected_role["value"] not in role_ids:
            load_story_role_to_generator(role_ids[0], announce=False)
        set_ui_status(tr("story_roles_loaded", count=len(role_ids)), "#0f7a2a")
        render_story_role_pool()

    def persist_single_role_memory(role_id: str, final_state: dict[str, Any]) -> None:
        final_text = str(final_state.get("final_story", "")).strip()
        if not final_text:
            return

        resolved_story = str(final_state.get("story_id", "")).strip() or story_id.value.strip() or "default"
        run_id = final_state.get("run_id")
        if run_id is not None:
            memory_story_id = f"generated_{resolved_story}_{run_id}"
        else:
            memory_story_id = f"generated_{resolved_story}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        memory_text = (
            "# Generated Story Memory\n\n"
            f"- role: {role_id}\n"
            f"- topic: {final_state.get('topic', topic.value)}\n"
            f"- style: {final_state.get('style', style.value)}\n"
            f"- story_id: {resolved_story}\n"
            f"- run_id: {final_state.get('run_id', 'n/a')}\n\n"
            "## Story\n\n"
            f"{final_text}\n"
        )

        add_role_memory_slice(role_id, memory_story_id, memory_text)
        set_ui_status(tr("story_memory_saved", role_id=role_id, story_id=memory_story_id), "#0f7a2a")

    def render_memory_slice_tabs(role_id: str) -> None:
        memory_slice_tabs.controls.clear()
        slice_ids = _list_role_memory_story_ids(role_id)

        if not slice_ids:
            selected_memory_slice["value"] = ""
            active_memory_slice_text.value = tr("active_memory_slice_none")
            memory_slice_tabs.controls.append(ft.Text(tr("no_memory_slices"), color="#666"))
            page.update()
            return

        if selected_memory_slice["value"] not in slice_ids:
            selected_memory_slice["value"] = slice_ids[0]

        active_memory_slice_text.value = tr("active_memory_slice", story_id=selected_memory_slice["value"])

        for sid in slice_ids:
            is_active = sid == selected_memory_slice["value"]

            def on_select_slice(_: ft.ControlEvent, story_id: str = sid) -> None:
                selected_memory_slice["value"] = story_id
                memory_story_id_input.value = story_id
                memory_text_input.value = _read_memory_slice(role_id, story_id)
                active_memory_slice_text.value = tr("active_memory_slice", story_id=story_id)
                set_ui_status(tr("memory_slice_loaded", role_id=role_id, story_id=story_id), "#0f7a2a")
                render_memory_slice_tabs(role_id)

            memory_slice_tabs.controls.append(
                ft.OutlinedButton(
                    sid,
                    disabled=is_active,
                    on_click=on_select_slice,
                )
            )

        page.update()

    def load_role_to_editor(role_id: str) -> None:
        role_id_input.value = role_id
        role_name_input.value = role_id
        profile_input.value = _read_role_profile(role_id)

        slice_ids = _list_role_memory_story_ids(role_id)
        if slice_ids:
            selected_memory_slice["value"] = slice_ids[0]
            memory_story_id_input.value = slice_ids[0]
            memory_text_input.value = _read_memory_slice(role_id, slice_ids[0])
            active_memory_slice_text.value = tr("active_memory_slice", story_id=slice_ids[0])
        else:
            selected_memory_slice["value"] = ""
            memory_story_id_input.value = ""
            memory_text_input.value = ""
            active_memory_slice_text.value = tr("active_memory_slice_none")

        render_memory_slice_tabs(role_id)
        set_ui_status(tr("role_loaded", role_id=role_id), "#0f7a2a")
        page.update()

    def handle_query_role_profile(_: ft.ControlEvent) -> None:
        role_name = role_name_input.value.strip()
        role_id = _find_role_id_by_name(role_name)
        if not role_id:
            set_ui_status(tr("role_not_found", name=role_name), "#a21515")
            return
        role_id_input.value = role_id
        profile_input.value = _read_role_profile(role_id)
        set_ui_status(tr("role_loaded", role_id=role_id), "#0f7a2a")
        page.update()

    def handle_load_role_by_name(_: ft.ControlEvent) -> None:
        role_name = role_name_input.value.strip()
        role_id = _find_role_id_by_name(role_name)
        if not role_id:
            set_ui_status(tr("role_not_found", name=role_name), "#a21515")
            return
        load_role_to_editor(role_id)

    def refresh_settings_snapshot() -> None:
        client = get_story_client()
        settings_base_url.value = client.base_url
        settings_model_planner.value = client.model_planner
        settings_model_role.value = client.model_role
        settings_model_integrator.value = client.model_integrator
        settings_model_quality.value = client.model_quality
        settings_log_dir.value = str(Path("logs").resolve())
        settings_opt_dir.value = str(Path("opt").resolve())
        page.update()

    def handle_health(_: ft.ControlEvent) -> None:
        result = get_story_client().health_check()
        health_text.value = (
            tr("health_ok", message=result.message)
            if result.ok
            else tr("health_failed", message=result.message)
        )
        health_text.color = "#0f7a2a" if result.ok else "#a21515"
        page.update()

    def handle_export(_: ft.ControlEvent) -> None:
        if not final_state_holder:
            set_ui_status(tr("export_nothing"), "#a21515")
            return

        opt_dir = Path("opt")
        opt_dir.mkdir(parents=True, exist_ok=True)
        run_id = final_state_holder.get("run_id")
        run_tag = str(run_id) if run_id is not None else datetime.now().strftime("%Y%m%d_%H%M%S")

        md_path = opt_dir / f"story_{run_tag}.md"
        json_path = opt_dir / f"story_{run_tag}.json"

        md_content = (
            f"# Story Export {run_tag}\n\n"
            f"- topic: {final_state_holder.get('topic', '')}\n"
            f"- style: {final_state_holder.get('style', '')}\n"
            f"- roles: {', '.join(final_state_holder.get('roles', []))}\n"
            f"- run_id: {final_state_holder.get('run_id', 'n/a')}\n"
            f"- log_file: {final_state_holder.get('log_file_path', 'n/a')}\n\n"
            "## Quality Report\n\n"
            f"{final_state_holder.get('quality_report', '')}\n\n"
            "## Final Story\n\n"
            f"{final_state_holder.get('final_story', '')}\n"
        )

        md_path.write_text(md_content, encoding="utf-8")
        json_path.write_text(
            json.dumps(final_state_holder, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        set_ui_status(tr("exported", md_path=md_path, json_path=json_path), "#0f7a2a")

    def handle_add_profile(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        if not role_id:
            set_ui_status(tr("role_id_required"), "#a21515")
            return
        profile_path = add_role_profile(role_id, profile_input.value)
        set_ui_status(tr("profile_saved", path=profile_path), "#0f7a2a")
        role_name_input.value = role_id
        render_roles()

    def handle_delete_profile(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        if not role_id:
            set_ui_status(tr("role_id_required"), "#a21515")
            return
        deleted = delete_role_profile(role_id)
        set_ui_status(
            tr("profile_deleted", deleted=deleted, role_id=role_id),
            "#0f7a2a" if deleted else "#a21515",
        )
        if deleted:
            profile_input.value = ""
        render_roles()
        page.update()

    def handle_add_memory(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        story = memory_story_id_input.value.strip()
        if not role_id or not story:
            set_ui_status(tr("role_story_required"), "#a21515")
            return
        path = add_role_memory_slice(role_id, story, memory_text_input.value)
        set_ui_status(tr("memory_saved", path=path), "#0f7a2a")
        selected_memory_slice["value"] = story
        render_memory_slice_tabs(role_id)

    def handle_delete_memory(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        story = memory_story_id_input.value.strip()
        if not role_id or not story:
            set_ui_status(tr("role_story_required"), "#a21515")
            return
        deleted = delete_role_memory_slice(role_id, story)
        set_ui_status(
            tr("memory_deleted", deleted=deleted, role_id=role_id, story_id=story),
            "#0f7a2a" if deleted else "#a21515",
        )
        if deleted and selected_memory_slice["value"] == story:
            selected_memory_slice["value"] = ""
            memory_story_id_input.value = ""
            memory_text_input.value = ""
        render_memory_slice_tabs(role_id)

    def handle_delete_all_memories(_: ft.ControlEvent) -> None:
        role_id = role_id_input.value.strip()
        if not role_id:
            set_ui_status(tr("role_id_required"), "#a21515")
            return
        count = delete_all_role_memories(role_id)
        set_ui_status(tr("memory_all_deleted", count=count, role_id=role_id), "#0f7a2a")
        selected_memory_slice["value"] = ""
        memory_story_id_input.value = ""
        memory_text_input.value = ""
        render_memory_slice_tabs(role_id)

    def apply_locale() -> None:
        page.title = tr("app_title")
        app_title_text.value = tr("app_title")
        app_subtitle_text.value = tr("app_subtitle")

        nav_story_button.content = tr("nav_story")
        nav_role_button.content = tr("nav_role")
        nav_settings_button.content = tr("nav_settings")

        story_id.label = tr("story_id")
        topic.label = tr("topic")
        style.label = tr("style")
        roles.label = tr("roles")
        max_retry.label = tr("max_retry")

        token_stream.label = tr("token_stream")
        event_stream_hint_text.value = tr("event_stream_hint")
        quality_report.label = tr("quality_report")
        final_story.label = tr("final_story")

        story_input_header.value = tr("story_input")
        event_stream_header.value = tr("event_stream")
        outputs_header.value = tr("outputs")
        history_header.value = tr("history")
        role_header.value = tr("role_management")
        roles_list_header.value = tr("roles_header")
        settings_header.value = tr("settings")

        run_single_button.content = tr("generate_single_story")
        run_single_quick_button.content = tr("generate_single_story")
        run_multi_button.content = tr("generate_multi_story")
        generation_single_tab_button.content = tr("generation_tab_single")
        generation_multi_tab_button.content = tr("generation_tab_multi")
        export_button.content = tr("export_opt")
        check_button.content = tr("check_health")
        query_framework_button.content = tr("query_framework")
        load_selected_framework_button.content = tr("framework_load")
        refresh_frameworks_button.content = tr("refresh_frameworks")
        story_framework_tab_button.content = tr("story_tab_framework")
        story_generation_tab_button.content = tr("story_tab_generation")
        load_story_role_button.content = tr("load_role_for_story")
        load_all_story_roles_single_button.content = tr("load_all_roles_for_story")
        load_all_story_roles_multi_button.content = tr("load_all_roles_for_story")
        refresh_history_button.content = tr("refresh_history")
        refresh_roles_button.content = tr("refresh_roles")
        refresh_settings_button.content = tr("refresh_settings")
        add_profile_button.content = tr("add_update_profile")
        delete_profile_button.content = tr("delete_profile")
        add_memory_button.content = tr("add_update_memory")
        delete_memory_button.content = tr("delete_memory")
        delete_all_memory_button.content = tr("delete_all_memories")
        query_profile_button.content = tr("role_query_profile")
        load_role_by_name_button.content = tr("role_load_by_name")

        role_id_input.label = tr("role_id")
        role_name_input.label = tr("role_name")
        story_role_name_input.label = tr("story_role_name")
        story_role_selector.label = tr("story_role_pool")
        profile_input.label = tr("role_profile")
        memory_story_id_input.label = tr("memory_story_id")
        memory_text_input.label = tr("memory_slice_text")
        story_framework_id_input.label = tr("framework_id")
        framework_selector.label = tr("frameworks_header")
        framework_preview_input.label = tr("framework_preview")
        story_mode_header.value = tr("story_mode")
        generation_subtabs_header.value = tr("generation_subtabs")
        generation_single_panel_header.value = tr("generation_single_panel")
        generation_multi_panel_header.value = tr("generation_multi_panel")
        frameworks_header_text.value = tr("frameworks_header")
        framework_guide_text.value = tr("story_framework_guide")
        generation_guide_text.value = tr("story_generation_guide")
        story_route_hint_text.value = tr(
            "story_route_hint",
            page=page_state["value"],
            story_tab=story_tab_state["value"],
            generation_tab=generation_tab_state["value"],
        )
        if resolved_framework_id["value"]:
            framework_resolved_text.value = tr("framework_resolved", story_id=resolved_framework_id["value"])
        else:
            framework_resolved_text.value = tr("framework_resolved_none")
        if story_generation_mode["value"] == "single":
            story_mode_text.value = tr("story_mode_single")
        else:
            story_mode_text.value = tr("story_mode_multi")
        if story_selected_role["value"]:
            story_selected_role_text.value = tr("selected_story_role", role_id=story_selected_role["value"])
        else:
            story_selected_role_text.value = tr("selected_story_role_none")
        memory_slice_header.value = tr("memory_slices")
        if selected_memory_slice["value"]:
            active_memory_slice_text.value = tr("active_memory_slice", story_id=selected_memory_slice["value"])
        else:
            active_memory_slice_text.value = tr("active_memory_slice_none")
        history_limit.label = tr("history_limit")

        language_dropdown.label = tr("language")
        settings_base_url.label = tr("setting_base_url")
        settings_model_planner.label = tr("setting_model_planner")
        settings_model_role.label = tr("setting_model_role")
        settings_model_integrator.label = tr("setting_model_integrator")
        settings_model_quality.label = tr("setting_model_quality")
        settings_log_dir.label = tr("setting_log_dir")
        settings_opt_dir.label = tr("setting_opt_dir")

        if not final_state_holder:
            status_text.value = tr("status_idle")
            run_meta_text.value = tr("run_meta_init")
            selected_run_text.value = tr("selected_run_none")
            ui_status_text.value = tr("ui_ready")
            ui_status_text.color = "#555"
        render_event_stream_hint()

        render_history()
        render_roles()
        render_frameworks()
        render_story_role_pool()
        current_role_id = role_id_input.value.strip()
        if current_role_id:
            render_memory_slice_tabs(current_role_id)
        page.update()

    def on_language_change(_: ft.ControlEvent) -> None:
        selected = language_dropdown.value or "zh"
        current_lang["value"] = selected if selected in I18N else "zh"
        apply_locale()

    def update_story_route_hint() -> None:
        story_route_hint_text.value = tr(
            "story_route_hint",
            page=page_state["value"],
            story_tab=story_tab_state["value"],
            generation_tab=generation_tab_state["value"],
        )

    def run_worker(selected_roles: list[str]) -> None:
        run_single_button.disabled = True
        run_single_quick_button.disabled = True
        run_multi_button.disabled = True
        status_text.value = tr("status_running")
        status_text.color = "#1f4e8c"
        event_stream_log.controls.clear()
        token_stream.value = ""
        final_story.value = ""
        quality_report.value = ""
        run_meta_text.value = tr("run_starting")
        page.update()

        try:
            if not selected_roles:
                raise ValueError(tr("story_roles_required"))

            state = build_input_state(
                story_id=story_id.value.strip() or "default",
                topic=topic.value.strip() or "an unexpected friendship",
                style=style.value.strip() or "warm",
                roles=selected_roles,
                max_retry=int(max_retry.value.strip() or "1"),
            )

            final_state: dict[str, Any] = dict(state)
            token_count = 0

            for event in stream_story_events(state):
                event_type = event.get("event", "")

                if event_type == "token":
                    text = str(event.get("text", ""))
                    token_count += max(len(text.split()), 1)
                    token_stream.value += text
                    if token_count % 12 == 0:
                        page.update()
                    continue

                if event_type == "node_update":
                    node = event.get("node", "")
                    data = event.get("data", {})
                    if isinstance(data, dict):
                        final_state.update(data)
                    keys = ", ".join(event.get("keys", []))
                    add_event_line(f"[node_update] {node} | keys: {keys}", "#1b365d")
                    continue

                if event_type == "node_log":
                    add_event_line(f"[node_log] {event.get('message', '')}", "#6a4a00")
                    continue

                if event_type == "error":
                    add_event_line(tr("stream_error", message=event.get("message", "")), "#a21515")
                    raise RuntimeError(str(event.get("message", "Unknown stream error")))

                if event_type == "done":
                    add_event_line(tr("stream_done"), "#0f7a2a")

            final_story.value = str(final_state.get("final_story", ""))
            quality_report.value = str(final_state.get("quality_report", ""))
            final_state_holder.clear()
            final_state_holder.update(final_state)
            run_meta_text.value = tr(
                "run_meta",
                run_id=final_state.get("run_id", "n/a"),
                db=final_state.get("sqlite_db_path", "n/a"),
                log=final_state.get("log_file_path", "n/a"),
            )
            status_text.value = tr("status_completed")
            status_text.color = "#0f7a2a"
            add_event_line(
                tr("summary_final_story", preview=_compact_preview(final_state.get("final_story", ""))),
                "#333",
            )
            render_history()

            if story_generation_mode["value"] == "single" and len(selected_roles) == 1:
                try:
                    persist_single_role_memory(selected_roles[0], final_state)
                except Exception as memory_exc:
                    add_event_line(tr("story_memory_save_failed", message=memory_exc), "#a21515")

        except Exception as exc:
            status_text.value = tr("status_failed", error=exc)
            status_text.color = "#a21515"
            add_event_line(tr("stream_exception", message=exc), "#a21515")
        finally:
            run_single_button.disabled = False
            run_single_quick_button.disabled = False
            run_multi_button.disabled = False
            render_event_stream_hint()
            page.update()

    def on_run_single(_: ft.ControlEvent) -> None:
        role_name = story_role_name_input.value.strip()
        role_id = (
            story_selected_role["value"]
            or _find_role_id_by_name(role_name)
            or (story_role_selector.value or "").strip()
        )
        if not role_id:
            set_ui_status(tr("story_role_required"), "#a21515")
            return

        story_generation_mode["value"] = "single"
        story_mode_text.value = tr("story_mode_single")
        load_story_role_to_generator(role_id, announce=False)
        render_story_role_pool()
        thread = threading.Thread(target=run_worker, args=([role_id],), daemon=True)
        thread.start()

    def on_run_multi(_: ft.ControlEvent) -> None:
        selected_roles = [item.strip() for item in roles.value.split(",") if item.strip()]
        if not selected_roles:
            set_ui_status(tr("story_roles_required"), "#a21515")
            return

        story_generation_mode["value"] = "multi"
        story_mode_text.value = tr("story_mode_multi")
        thread = threading.Thread(target=run_worker, args=(selected_roles,), daemon=True)
        thread.start()

    run_single_button.on_click = on_run_single
    run_single_quick_button.on_click = on_run_single
    run_multi_button.on_click = on_run_multi
    check_button.on_click = handle_health
    export_button.on_click = handle_export

    add_profile_button = ft.OutlinedButton("Add/Update Profile", on_click=handle_add_profile)
    delete_profile_button = ft.OutlinedButton("Delete Profile", on_click=handle_delete_profile)
    add_memory_button = ft.OutlinedButton("Add/Update Memory", on_click=handle_add_memory)
    delete_memory_button = ft.OutlinedButton("Delete Memory", on_click=handle_delete_memory)
    delete_all_memory_button = ft.OutlinedButton("Delete All Memories", on_click=handle_delete_all_memories)
    query_profile_button = ft.OutlinedButton("Query Profile", on_click=handle_query_role_profile)
    load_role_by_name_button = ft.OutlinedButton("Load By Name", on_click=handle_load_role_by_name)
    query_framework_button = ft.OutlinedButton("Query Framework", on_click=handle_query_framework)
    load_selected_framework_button = ft.OutlinedButton("Load Framework", on_click=handle_load_selected_framework)
    refresh_frameworks_button = ft.OutlinedButton("Refresh Frameworks", on_click=lambda _: render_frameworks())
    load_story_role_button = ft.OutlinedButton("Load Role To Generator", on_click=handle_load_story_role_by_name)
    load_all_story_roles_single_button = ft.OutlinedButton("Load All Roles", on_click=handle_load_all_story_roles)
    load_all_story_roles_multi_button = ft.OutlinedButton("Load All Roles", on_click=handle_load_all_story_roles)
    story_framework_tab_button = ft.OutlinedButton("Framework")
    story_generation_tab_button = ft.OutlinedButton("Generation")
    generation_single_tab_button = ft.OutlinedButton("Single-Role")
    generation_multi_tab_button = ft.OutlinedButton("Multi-Role")
    refresh_history_button = ft.OutlinedButton("Refresh History", on_click=lambda _: render_history())
    refresh_roles_button = ft.OutlinedButton("Refresh Roles", on_click=lambda _: render_roles())
    refresh_settings_button = ft.OutlinedButton("Refresh Settings", on_click=lambda _: refresh_settings_snapshot())

    memory_slice_header = ft.Text(tr("memory_slices"), size=16, weight=ft.FontWeight.W_600)
    story_mode_header = ft.Text(tr("story_mode"), size=16, weight=ft.FontWeight.W_600)
    generation_subtabs_header = ft.Text(tr("generation_subtabs"), size=16, weight=ft.FontWeight.W_600)
    generation_single_panel_header = ft.Text(tr("generation_single_panel"), size=15, weight=ft.FontWeight.W_600)
    generation_multi_panel_header = ft.Text(tr("generation_multi_panel"), size=15, weight=ft.FontWeight.W_600)
    story_mode_text = ft.Text(tr("story_mode_multi"), color="#555")
    frameworks_header_text = ft.Text(tr("frameworks_header"), size=16, weight=ft.FontWeight.W_600)
    framework_guide_text = ft.Text(tr("story_framework_guide"), color="#5a6780", size=11)
    generation_guide_text = ft.Text(tr("story_generation_guide"), color="#5a6780", size=11)

    language_dropdown = ft.Dropdown(
        label=tr("language"),
        value=current_lang["value"],
        width=220,
        options=[
            ft.dropdown.Option(key="zh", text="中文"),
            ft.dropdown.Option(key="en", text="English"),
        ],
        on_select=on_language_change,
    )

    framework_selector.on_select = handle_framework_selector
    story_role_selector.on_select = handle_story_role_selector

    generation_row_1 = ft.Row([story_id, style, max_retry], wrap=True)
    generation_row_2 = ft.Row([topic], wrap=True)
    generation_row_3 = ft.Row([roles], wrap=True)
    generation_role_row = ft.Row([story_role_name_input, story_role_selector, load_story_role_button], wrap=True)
    generation_action_row = ft.Row(
        [run_single_quick_button, export_button, status_text],
        alignment=ft.MainAxisAlignment.START,
        wrap=True,
    )

    framework_query_row = ft.Row([story_framework_id_input, query_framework_button, refresh_frameworks_button], wrap=True)
    framework_select_row = ft.Row([framework_selector, load_selected_framework_button], wrap=True)

    story_framework_tab = ft.Container(
        visible=True,
        expand=True,
        padding=12,
        border_radius=10,
        border=ft.Border.all(1, "#d7dce5"),
        bgcolor="#ffffff",
        content=ft.Column(
            [
                framework_guide_text,
                framework_query_row,
                framework_select_row,
                framework_resolved_text,
                framework_preview_input,
            ],
            spacing=10,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    generation_single_tab = ft.Container(
        visible=True,
        expand=True,
        padding=12,
        border_radius=10,
        border=ft.Border.all(1, "#d7dce5"),
        bgcolor="#ffffff",
        content=ft.Column(
            [
                generation_single_panel_header,
                story_selected_role_text,
                ft.Row([load_all_story_roles_single_button, run_single_button], wrap=True),
            ],
            expand=True,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    generation_multi_tab = ft.Container(
        visible=True,
        expand=True,
        padding=12,
        border_radius=10,
        border=ft.Border.all(1, "#d7dce5"),
        bgcolor="#ffffff",
        content=ft.Column(
            [
                generation_multi_panel_header,
                generation_row_3,
                ft.Row([load_all_story_roles_multi_button], wrap=True),
                ft.Row([run_multi_button], wrap=True),
            ],
            expand=True,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    generation_tab_host = ft.Container(
        height=190,
        padding=4,
        content=generation_multi_tab,
    )

    story_generation_tab = ft.Container(
        visible=True,
        expand=True,
        padding=12,
        border_radius=10,
        border=ft.Border.all(1, "#d7dce5"),
        bgcolor="#ffffff",
        content=ft.Column(
            [
                generation_guide_text,
                generation_row_1,
                generation_row_2,
                generation_role_row,
                story_mode_header,
                story_mode_text,
                generation_subtabs_header,
                ft.Row([generation_single_tab_button, generation_multi_tab_button], wrap=True),
                generation_tab_host,
                generation_action_row,
            ],
            expand=True,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    story_tab_host = ft.Container(
        height=430,
        padding=8,
        border_radius=10,
        border=ft.Border.all(1, "#d7dce5"),
        bgcolor="#ffffff",
        content=story_generation_tab,
    )

    story_page = ft.Container(
        visible=True,
        expand=True,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            expand=2,
                            padding=14,
                            border_radius=14,
                            bgcolor="#ffffff",
                            border=ft.Border.all(1, "#dfe4ed"),
                            content=ft.Column(
                                [
                                    story_input_header,
                                    ft.Row([story_framework_tab_button, story_generation_tab_button], wrap=True),
                                    story_route_hint_text,
                                    story_tab_host,
                                    run_meta_text,
                                    ui_status_text,
                                    ft.Container(
                                        border=ft.Border.all(1, "#d7dce5"),
                                        border_radius=10,
                                        padding=10,
                                        bgcolor="#ffffff",
                                        content=ft.Column(
                                            [
                                                event_stream_header,
                                                ft.Container(
                                                    content=event_stream_log,
                                                    border=ft.Border.all(1, "#d7dce5"),
                                                    border_radius=8,
                                                    padding=8,
                                                    bgcolor="#ffffff",
                                                    height=96,
                                                ),
                                            ],
                                            spacing=8,
                                        ),
                                    ),
                                ],
                                spacing=12,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                        ),
                        ft.Container(
                            expand=3,
                            padding=14,
                            border_radius=14,
                            bgcolor="#ffffff",
                            border=ft.Border.all(1, "#dfe4ed"),
                            content=ft.Column(
                                [
                                    outputs_header,
                                    token_stream,
                                    quality_report,
                                    final_story,
                                    ft.Divider(),
                                    history_header,
                                    ft.Row([history_limit, refresh_history_button], wrap=True),
                                    selected_run_text,
                                    ft.Container(
                                        content=history_log,
                                        border=ft.Border.all(1, "#d7dce5"),
                                        padding=8,
                                        border_radius=10,
                                        height=180,
                                    ),
                                ],
                                expand=True,
                                spacing=12,
                            ),
                        ),
                    ],
                    expand=True,
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    role_page = ft.Container(
        visible=False,
        expand=True,
        padding=14,
        border_radius=14,
        bgcolor="#ffffff",
        border=ft.Border.all(1, "#dfe4ed"),
        content=ft.Column(
            [
                role_header,
                ft.Row([role_name_input, query_profile_button, load_role_by_name_button], wrap=True),
                ft.Row([role_id_input, memory_story_id_input, refresh_roles_button], wrap=True),
                profile_input,
                memory_slice_header,
                active_memory_slice_text,
                memory_slice_tabs,
                memory_text_input,
                ft.Row([add_profile_button, delete_profile_button], wrap=True),
                ft.Row([add_memory_button, delete_memory_button, delete_all_memory_button], wrap=True),
                roles_list_header,
                ft.Container(
                    content=role_list,
                    border=ft.Border.all(1, "#d7dce5"),
                    padding=8,
                    border_radius=10,
                    expand=True,
                ),
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    settings_base_url = ft.TextField(label="OLLAMA_BASE_URL", read_only=True)
    settings_model_planner = ft.TextField(label="OLLAMA_MODEL_PLANNER", read_only=True)
    settings_model_role = ft.TextField(label="OLLAMA_MODEL_ROLE", read_only=True)
    settings_model_integrator = ft.TextField(label="OLLAMA_MODEL_INTEGRATOR", read_only=True)
    settings_model_quality = ft.TextField(label="OLLAMA_MODEL_QUALITY", read_only=True)
    settings_log_dir = ft.TextField(label="Log Directory", read_only=True)
    settings_opt_dir = ft.TextField(label="Export Directory", read_only=True)

    settings_page = ft.Container(
        visible=False,
        expand=True,
        padding=14,
        border_radius=14,
        bgcolor="#ffffff",
        border=ft.Border.all(1, "#dfe4ed"),
        content=ft.Column(
            [
                settings_header,
                ft.Row([language_dropdown, check_button, refresh_settings_button], wrap=True),
                health_text,
                settings_base_url,
                settings_model_planner,
                settings_model_role,
                settings_model_integrator,
                settings_model_quality,
                settings_log_dir,
                settings_opt_dir,
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    def switch_story_tab(target: str) -> None:
        story_tab_state["value"] = "framework" if target == "framework" else "generation"
        story_tab_host.content = story_framework_tab if story_tab_state["value"] == "framework" else story_generation_tab
        story_framework_tab_button.disabled = story_tab_state["value"] == "framework"
        story_generation_tab_button.disabled = story_tab_state["value"] == "generation"
        update_story_route_hint()
        page.update()

    def switch_generation_tab(target: str) -> None:
        generation_tab_state["value"] = "single" if target == "single" else "multi"
        generation_tab_host.content = generation_single_tab if generation_tab_state["value"] == "single" else generation_multi_tab
        generation_single_tab_button.disabled = generation_tab_state["value"] == "single"
        generation_multi_tab_button.disabled = generation_tab_state["value"] == "multi"
        story_generation_mode["value"] = generation_tab_state["value"]
        story_mode_text.value = tr("story_mode_single") if generation_tab_state["value"] == "single" else tr("story_mode_multi")
        update_story_route_hint()
        page.update()

    def switch_page(target: str) -> None:
        page_state["value"] = "story" if target == "story" else ("role" if target == "role" else "settings")
        story_page.visible = target == "story"
        role_page.visible = target == "role"
        settings_page.visible = target == "settings"

        nav_story_button.disabled = story_page.visible
        nav_role_button.disabled = role_page.visible
        nav_settings_button.disabled = settings_page.visible
        update_story_route_hint()
        page.update()

    nav_story_button.on_click = lambda _: switch_page("story")
    nav_role_button.on_click = lambda _: switch_page("role")
    nav_settings_button.on_click = lambda _: switch_page("settings")
    story_framework_tab_button.on_click = lambda _: switch_story_tab("framework")
    story_generation_tab_button.on_click = lambda _: switch_story_tab("generation")
    generation_single_tab_button.on_click = lambda _: switch_generation_tab("single")
    generation_multi_tab_button.on_click = lambda _: switch_generation_tab("multi")

    page.add(
        ft.Column(
            [
                app_title_text,
                app_subtitle_text,
                ft.Row([nav_story_button, nav_role_button, nav_settings_button], wrap=True),
                story_page,
                role_page,
                settings_page,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
    )

    render_history()
    render_roles()
    render_frameworks()
    render_event_stream_hint()
    load_framework_to_editor(story_id.value, announce=False)
    initial_roles = [item.strip() for item in roles.value.split(",") if item.strip()]
    available_roles = set(discover_roles("role"))
    if initial_roles and initial_roles[0] in available_roles:
        load_story_role_to_generator(initial_roles[0], announce=False)
    render_story_role_pool()
    refresh_settings_snapshot()
    apply_locale()
    switch_generation_tab("multi")
    switch_story_tab("generation")
    switch_page("story")


if __name__ == "__main__":
    ft.run(main)
