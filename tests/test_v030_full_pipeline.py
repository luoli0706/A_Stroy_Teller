"""
Alpha 0.3 全流程集成测试
========================

验证从「输入故事框架 + 角色模板」到「输出最终故事」的完整链路。

Alpha 0.3 核心变更（相对于 v0.2.x）：
  1. [新增节点] generate_established_facts —— 从全局大纲提炼既定事实时间线与世界观
  2. [新增节点] index_facts_for_rag        —— 将既定事实写入向量库（ChromaDB）和文件元数据库（SQLite）
  3. [重构节点] retrieve_role_rag_contexts  —— 混合检索（向量 + 文件）：角色私有记忆 + __facts__ + __world__
  4. [重构节点] integrate_perspectives      —— 基于章节 + 既定事实锚点的分段整合策略

测试范围：
  - 所有 16 个节点均按序执行完毕
  - v0.3 新增 state 字段（established_facts / world_bible / rag_facts_indexed / story_chapters）
  - 混合 RAG 链路（向量 + 文件双通道）
  - 文件落盘结构（facts 目录 / role 切片目录 / final 目录）
  - 长文本指标（字数 / 段落 / 句子）
  - DB checkpoint 持久化
"""

import os
import time
import unittest
from pathlib import Path

from app.config import OPT_STORIES_DIR
from app.runtime import build_input_state, get_thread_history_async, stream_story_events_async

# ── 测试参数（支持环境变量覆盖） ───────────────────────────────────────────────
_STORY_ID = "cat_world"
_ROLES = ["Reshaely", "VanlyShan", "SolinXuan"]
_TOPIC = "修复星绒乐园的失控裂隙，揭示星绒本源的真相"
_STYLE = "治愈奇幻，偏长篇，细节丰富，多角色协作"

# 长文本质量阈值（可通过环境变量覆盖）
# _MIN_FINAL_CHARS  : 最终故事总字数下限。Alpha 0.3 多角色章节化整合后预期产出量。
# _MIN_ROLE_CHARS   : 单角色视角草稿字数下限。并发生成时每个角色的最低内容量。
# _MIN_PARAGRAPHS   : 最终故事段落数下限（非空行计数）。用于检测内容是否被截断。
# _MIN_SENTENCES    : 最终故事句子数下限（按常见中文标点计数）。
_MIN_FINAL_CHARS = int(os.getenv("TEST_MIN_FINAL_STORY_CHARS", "1500"))
_MIN_ROLE_CHARS = int(os.getenv("TEST_MIN_ROLE_DRAFT_CHARS", "300"))
_MIN_PARAGRAPHS = int(os.getenv("TEST_MIN_STORY_PARAGRAPHS", "5"))
_MIN_SENTENCES = int(os.getenv("TEST_MIN_STORY_SENTENCES", "15"))

# Alpha 0.3 期望的完整节点序列（有序）
_EXPECTED_NODES_IN_ORDER = [
    "collect_requirements",
    "load_story_framework",
    "load_roles",
    "index_role_memories_for_rag",
    "map_roles_to_slots",
    "plan_global_story",
    "generate_established_facts",   # [v0.3] 新增
    "index_facts_for_rag",          # [v0.3] 新增
    "wait_for_user_outline",
    "adapt_roles_to_framework",
    "retrieve_role_rag_contexts",
    "generate_role_views",
    "integrate_perspectives",
    "quality_check",
    "finalize_output",
    "distill_memories",
]


def _story_metrics(text: str) -> dict:
    cleaned = (text or "").strip()
    paragraphs = [ln for ln in cleaned.splitlines() if ln.strip()]
    sentence_marks = "。！？!?；;"
    sentence_count = sum(cleaned.count(m) for m in sentence_marks)
    return {
        "char_count": len(cleaned),
        "paragraph_count": len(paragraphs),
        "sentence_count": sentence_count,
    }


class TestV030FullPipeline(unittest.IsolatedAsyncioTestCase):
    """Alpha 0.3 全流程集成测试。"""

    async def test_full_pipeline_cat_world(self):
        thread_id = f"v030_full_{int(time.time())}"

        print(f"\n{'='*60}")
        print(f"[Alpha 0.3 全流程测试] thread_id={thread_id}")
        print(f"story_id={_STORY_ID}  roles={_ROLES}")
        print(f"{'='*60}")

        state = build_input_state(
            story_id=_STORY_ID,
            topic=_TOPIC,
            style=_STYLE,
            roles=_ROLES,
            max_retry=1,
            rag_enabled=True,
            rag_top_k=4,
        )

        # ── 收集事件流数据 ────────────────────────────────────────────────────
        nodes_completed: list[str] = []
        token_chars: int = 0

        # 各节点产出的 state 片段
        node_data: dict[str, dict] = {}

        try:
            async for event in stream_story_events_async(state, thread_id=thread_id):
                etype = event.get("event")

                if etype == "node_start":
                    print(f"\n[NODE-START] {event.get('node')}")

                elif etype == "token":
                    text = event.get("text") or ""
                    token_chars += len(text)
                    print(text, end="", flush=True)

                elif etype == "node_update":
                    node = event.get("node", "")
                    data = event.get("data", {})
                    nodes_completed.append(node)
                    node_data[node] = data
                    print(f"\n[NODE-DONE] {node}")

                elif etype == "error":
                    self.fail(f"流程中断，节点错误: {event.get('message')}")

                elif etype == "done":
                    print("\n[DONE] 事件流正常结束")

        except Exception as exc:
            self.fail(f"stream_story_events_async 抛出异常: {exc}")

        # ════════════════════════════════════════════════════════════════════
        # 1. 节点完整性验证
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[节点列表] 已完成={nodes_completed}")
        self.assertGreater(len(nodes_completed), 0, "没有任何节点执行完成")

        for expected_node in _EXPECTED_NODES_IN_ORDER:
            self.assertIn(
                expected_node,
                nodes_completed,
                f"[链路缺失] 节点 '{expected_node}' 未执行，Alpha 0.3 链路不完整",
            )

        # 节点顺序验证（确认已完成节点中，期望节点的相对顺序严格递增）
        expected_positions = [
            nodes_completed.index(n) for n in _EXPECTED_NODES_IN_ORDER
        ]
        self.assertEqual(
            expected_positions,
            sorted(expected_positions),
            "节点执行顺序不符合 Alpha 0.3 定义的 DAG 顺序",
        )

        # ════════════════════════════════════════════════════════════════════
        # 2. 框架加载验证
        # ════════════════════════════════════════════════════════════════════
        fw_data = node_data.get("load_story_framework", {})
        loaded_story_id = fw_data.get("story_id", "")
        loaded_framework = fw_data.get("story_framework", "")
        print(f"\n[框架] story_id={loaded_story_id}, chars={len(loaded_framework)}")

        self.assertEqual(loaded_story_id, _STORY_ID, "加载的框架 story_id 不匹配")
        self.assertTrue(loaded_framework.strip(), "story_framework 为空，未读取框架文本")
        self.assertIn("星绒乐园", loaded_framework, "框架文本不包含 cat_world 核心内容")

        # ════════════════════════════════════════════════════════════════════
        # 3. 角色加载验证
        # ════════════════════════════════════════════════════════════════════
        role_data = node_data.get("load_roles", {})
        role_assets = role_data.get("role_assets", {})
        for rid in _ROLES:
            self.assertIn(rid, role_assets, f"角色 {rid} 未被加载")
            self.assertTrue(
                role_assets[rid].get("profile", "").strip(),
                f"角色 {rid} 的 profile 为空",
            )
        print(f"[角色] 已加载 {len(role_assets)} 个角色档案")

        # ════════════════════════════════════════════════════════════════════
        # 4. 全局大纲验证
        # ════════════════════════════════════════════════════════════════════
        global_outline = node_data.get("plan_global_story", {}).get("global_outline", "")
        self.assertTrue(global_outline.strip(), "global_outline 为空")
        # 最低语义锚定：大纲应包含 cat_world 核心关键词之一
        outline_hits = [kw for kw in ["星绒", "乐园", "裂隙"] if kw in global_outline]
        self.assertTrue(outline_hits, "global_outline 未提及 cat_world 核心关键词，可能未利用框架")
        print(f"[大纲] chars={len(global_outline)}, keywords={outline_hits}")

        # ════════════════════════════════════════════════════════════════════
        # 5. [v0.3] 既定事实节点验证
        # ════════════════════════════════════════════════════════════════════
        facts_data = node_data.get("generate_established_facts", {})
        established_facts = facts_data.get("established_facts", "")
        world_bible = facts_data.get("world_bible", "")
        print(f"\n[v0.3 既定事实] established_facts chars={len(established_facts)}, world_bible chars={len(world_bible)}")

        self.assertTrue(
            established_facts.strip(),
            "[v0.3] established_facts 为空 —— generate_established_facts 节点未正常产出",
        )
        # world_bible 允许为空（LLM 有时不生成该段），但 established_facts 必须存在

        # ════════════════════════════════════════════════════════════════════
        # 6. [v0.3] 事实索引节点验证
        # ════════════════════════════════════════════════════════════════════
        rag_facts_data = node_data.get("index_facts_for_rag", {})
        rag_facts_indexed = rag_facts_data.get("rag_facts_indexed", -1)
        print(f"[v0.3 RAG 事实索引] rag_facts_indexed={rag_facts_indexed}")

        self.assertGreaterEqual(
            rag_facts_indexed,
            0,
            "[v0.3] rag_facts_indexed 未返回（index_facts_for_rag 节点未执行）",
        )
        # 首次运行必须索引 > 0 条；重复运行相同内容时可能为 0（hash 命中）
        # 因此这里只做「已执行」的断言，不强制 > 0

        # ════════════════════════════════════════════════════════════════════
        # 7. 角色适配与关系网验证
        # ════════════════════════════════════════════════════════════════════
        adapt_data = node_data.get("adapt_roles_to_framework", {})
        role_identities = adapt_data.get("role_story_identities", {})
        rel_matrix = adapt_data.get("relationship_matrix", "")

        for rid in _ROLES:
            self.assertIn(rid, role_identities, f"角色 {rid} 缺少 story_identity 适配")
            identity = role_identities[rid]
            self.assertIn("story_name", identity, f"角色 {rid} identity 缺少 story_name 字段")
        self.assertTrue(rel_matrix.strip(), "relationship_matrix 为空")
        print(f"[角色适配] 已适配 {len(role_identities)} 个角色，关系网 chars={len(rel_matrix)}")

        # ════════════════════════════════════════════════════════════════════
        # 8. [v0.3] 混合 RAG 上下文验证
        # ════════════════════════════════════════════════════════════════════
        rag_ctx_data = node_data.get("retrieve_role_rag_contexts", {})
        rag_role_contexts = rag_ctx_data.get("rag_role_contexts", {})
        print(f"\n[v0.3 混合 RAG] 检索到角色上下文数={len(rag_role_contexts)}")

        # 所有角色都应有 RAG 上下文条目（可以是空字符串，但键必须存在）
        for rid in _ROLES:
            self.assertIn(
                rid,
                rag_role_contexts,
                f"[v0.3] 角色 {rid} 缺少 rag_role_contexts 条目，混合检索未覆盖该角色",
            )

        # ════════════════════════════════════════════════════════════════════
        # 9. 角色视角草稿验证
        # ════════════════════════════════════════════════════════════════════
        role_views_data = node_data.get("generate_role_views", {})
        role_view_drafts = role_views_data.get("role_view_drafts", {})

        self.assertEqual(
            set(role_view_drafts.keys()),
            set(_ROLES),
            "角色视角草稿集合与输入角色不一致",
        )
        for rid in _ROLES:
            draft = role_view_drafts.get(rid, "")
            self.assertGreaterEqual(
                len(draft.strip()),
                _MIN_ROLE_CHARS,
                f"角色 {rid} 草稿长度 {len(draft)} 不足，预期 >= {_MIN_ROLE_CHARS}",
            )
        print(f"[角色草稿] 所有 {len(_ROLES)} 个角色草稿通过长度验证")

        # ════════════════════════════════════════════════════════════════════
        # 10. [v0.3] story_chapters 验证
        # ════════════════════════════════════════════════════════════════════
        integrate_data = node_data.get("integrate_perspectives", {})
        story_chapters = integrate_data.get("story_chapters", [])
        integrated_draft = integrate_data.get("integrated_draft", "")
        print(f"\n[v0.3 章节整合] story_chapters 数量={len(story_chapters)}, integrated_draft chars={len(integrated_draft)}")

        self.assertTrue(
            integrated_draft.strip(),
            "integrated_draft 为空，integrate_perspectives 节点未正常产出",
        )
        self.assertIsInstance(story_chapters, list, "story_chapters 应为列表")
        # 章节数可为 1（当既定事实无章节标记时降级），但必须存在
        self.assertGreater(len(story_chapters), 0, "[v0.3] story_chapters 为空列表")

        # ════════════════════════════════════════════════════════════════════
        # 11. 质量检查验证
        # ════════════════════════════════════════════════════════════════════
        qa_data = node_data.get("quality_check", {})
        quality_report = qa_data.get("quality_report", {})
        is_report_dict = isinstance(quality_report, dict)
        quality_status = quality_report.get("status", "") if is_report_dict else ""
        quality_score = quality_report.get("score") if is_report_dict else None
        print(f"[质量检查] status={quality_status}, score={quality_score}")

        self.assertIn(
            quality_status,
            {"PASS", "FAIL", ""},
            f"quality_report.status 非法值: {quality_status}",
        )

        # ════════════════════════════════════════════════════════════════════
        # 12. 最终输出验证（state 层）
        # ════════════════════════════════════════════════════════════════════
        finalize_data = node_data.get("finalize_output", {})
        final_story = finalize_data.get("final_story", "")
        run_id = finalize_data.get("run_id")
        final_story_path_str = finalize_data.get("final_story_path", "")
        role_story_paths = finalize_data.get("role_story_paths", {})

        print(f"\n[最终输出] chars={len(final_story)}, run_id={run_id}")

        self.assertTrue(final_story.strip(), "final_story 为空")
        self.assertIsNotNone(run_id, "run_id 未返回，持久化可能未完成")
        self.assertTrue(final_story_path_str, "final_story_path 未返回")

        # ════════════════════════════════════════════════════════════════════
        # 13. 长文本指标验证
        # ════════════════════════════════════════════════════════════════════
        metrics = _story_metrics(final_story)
        print(f"[长文本指标] {metrics}")

        self.assertGreaterEqual(
            metrics["char_count"],
            _MIN_FINAL_CHARS,
            f"最终故事长度 {metrics['char_count']} 不足，预期 >= {_MIN_FINAL_CHARS}",
        )
        self.assertGreaterEqual(
            metrics["paragraph_count"],
            _MIN_PARAGRAPHS,
            f"段落数 {metrics['paragraph_count']} 不足，预期 >= {_MIN_PARAGRAPHS}",
        )
        self.assertGreaterEqual(
            metrics["sentence_count"],
            _MIN_SENTENCES,
            f"句子数 {metrics['sentence_count']} 不足，预期 >= {_MIN_SENTENCES}",
        )

        # 最终故事语义锚定（至少包含一个 cat_world 核心关键词）
        story_hits = [kw for kw in ["星绒", "乐园", "裂隙"] if kw in final_story]
        self.assertTrue(story_hits, "最终故事缺少 cat_world 核心语义关键词，内容可能偏题")

        # ════════════════════════════════════════════════════════════════════
        # 14. 文件落盘结构验证
        # ════════════════════════════════════════════════════════════════════
        print("\n[文件落盘验证]")

        # 14a. 最终故事文件
        final_path = Path(final_story_path_str)
        self.assertTrue(final_path.exists(), f"最终故事文件不存在: {final_path}")
        self.assertEqual(final_path.parent.name, "final", "最终故事文件未落在 final 目录")
        self.assertEqual(final_path.parent.parent.name, _STORY_ID, "最终故事文件的根目录不是 story_id")
        print(f"  ✓ 最终故事: {final_path}")

        # 14b. [v0.3] 既定事实文件
        facts_dir = OPT_STORIES_DIR / _STORY_ID / "facts"
        facts_file = facts_dir / f"facts_run{run_id}.md"
        self.assertTrue(
            facts_file.exists(),
            f"[v0.3] 既定事实文件不存在: {facts_file}",
        )
        facts_content = facts_file.read_text(encoding="utf-8")
        self.assertIn(
            "__facts__",
            facts_content,
            "[v0.3] 既定事实文件缺少 Role ID: __facts__ 标记",
        )
        print(f"  ✓ 既定事实文件: {facts_file}")

        # 14c. 角色切片文件
        for rid in _ROLES:
            role_path_str = role_story_paths.get(rid, "")
            self.assertTrue(role_path_str, f"角色 {rid} 的输出路径缺失")
            role_path = Path(role_path_str)
            self.assertTrue(role_path.exists(), f"角色 {rid} 切片文件不存在: {role_path}")
            self.assertEqual(role_path.parent.name, rid, f"角色 {rid} 文件未落在对应角色目录")
            self.assertEqual(role_path.parent.parent.name, _STORY_ID, f"角色 {rid} 文件根目录不是 story_id")
            # 命名约定由 persist_generated_role_slice 决定：chapter_{timestamp}_run{run_id}.md
            self.assertTrue(role_path.name.startswith("chapter_"), f"角色 {rid} 文件名未以 chapter_ 开头")
            print(f"  ✓ 角色切片 [{rid}]: {role_path}")

        # ════════════════════════════════════════════════════════════════════
        # 15. Token 流验证（模型确实在输出）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[Token 流] 总 token 字符数={token_chars}")
        self.assertGreater(token_chars, 200, "Token 流输出过少，LLM 可能未正常生成")

        # ════════════════════════════════════════════════════════════════════
        # 16. Checkpoint 持久化验证
        # ════════════════════════════════════════════════════════════════════
        history = await get_thread_history_async(thread_id)
        self.assertGreater(len(history), 0, "线程历史为空，LangGraph checkpoint 持久化可能失败")
        print(f"[Checkpoint] 历史条目数={len(history)}")

        print(
            f"\n{'='*60}\n[SUCCESS] Alpha 0.3 全流程测试通过 "
            f"| chars={metrics['char_count']} | paragraphs={metrics['paragraph_count']} "
            f"| qa={quality_status}:{quality_score} | chapters={len(story_chapters)}\n{'='*60}"
        )


if __name__ == "__main__":
    unittest.main()
