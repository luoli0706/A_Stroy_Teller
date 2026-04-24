"""
v0.3 全流程集成测试
=================

验证从「故事框架 + 角色模板」输入到「最终故事」输出的完整链路完整性。

v0.3 关键架构变化（相对于 v0.2.x）：
  1. 新增 generate_established_facts 节点：从全局大纲提炼客观事实时间线（established_facts）
     和世界观设定（world_bible），作为所有角色视角生成的权威锚点。
  2. 新增 index_facts_for_rag 节点：将既定事实和世界观同时写入：
       - 物理文件（opt/stories/{story_id}/facts/facts_run{N}.md）
       - SQLite 元数据库（chunks 表）
       - Chroma 向量库（story_memory_slices 集合）
  3. retrieve_role_rag_contexts 改为调用 hybrid_search_async：
       向量检索（Chroma）+ 文件元数据检索（SQLite）并行执行，结果融合。
       每个角色的检索范围：私有记忆 + __facts__ + __world__ 文档。
  4. integrate_perspectives 改为 integrate_by_chapters_async：
       将 established_facts 按章节（Act/Chapter）切分为锚点，逐章调用 LLM 整合，
       化解一次性发送全部角色草稿导致的上下文窗口压力。
  5. StoryState 新增字段：established_facts / world_bible / rag_facts_indexed / story_chapters。

完整链路（16 节点顺序）：
  collect_requirements → load_story_framework → load_roles →
  index_role_memories_for_rag → map_roles_to_slots → plan_global_story →
  generate_established_facts → index_facts_for_rag →
  wait_for_user_outline → adapt_roles_to_framework →
  retrieve_role_rag_contexts → generate_role_views →
  integrate_perspectives → quality_check →
  finalize_output → distill_memories

测试场景：cat_world 故事框架 + 三角色（Reshaely / VanlyShan / SolinXuan）
"""

import os
import time
import unittest
from pathlib import Path

from app.runtime import build_input_state, get_thread_history_async, stream_story_events_async
from app.observability import create_run_logger, log_event

# ── 可通过环境变量调整的阈值 ──────────────────────────────────────────────────
_MIN_FINAL_CHARS = int(os.getenv("TEST_MIN_FINAL_STORY_CHARS", "1500"))
_MIN_ROLE_DRAFT_CHARS = int(os.getenv("TEST_MIN_ROLE_DRAFT_CHARS", "300"))
_MIN_PARAGRAPHS = int(os.getenv("TEST_MIN_STORY_PARAGRAPHS", "5"))
_MIN_SENTENCES = int(os.getenv("TEST_MIN_STORY_SENTENCES", "15"))
_MIN_TOKEN_CHARS = int(os.getenv("TEST_MIN_TOKEN_CHARS", "200"))

# v0.3 链路中必须依次出现的节点（顺序敏感）。
# wait_for_user_outline 是仅返回当前状态的 passthrough 节点，astream_events 不一定为其
# 产生独立的 on_chain_update 事件，因此从必检节点列表中省略，仅通过其前后节点顺序来
# 间接验证其位置正确。
_REQUIRED_NODES_ORDERED = [
    "collect_requirements",
    "load_story_framework",
    "load_roles",
    "index_role_memories_for_rag",
    "map_roles_to_slots",
    "plan_global_story",
    "generate_established_facts",   # [v0.3] 新增
    "index_facts_for_rag",          # [v0.3] 新增
    "adapt_roles_to_framework",
    "retrieve_role_rag_contexts",   # [v0.3] 混合检索
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
    sentences = sum(cleaned.count(m) for m in sentence_marks)
    return {
        "char_count": len(cleaned),
        "paragraph_count": len(paragraphs),
        "sentence_count": sentences,
    }


class TestV030FullPipeline(unittest.IsolatedAsyncioTestCase):
    """v0.3 全流程集成测试：cat_world 三角色，全链路节点与产物验证。"""

    # ── 测试参数 ──────────────────────────────────────────────────────────────
    STORY_ID = "cat_world"
    ROLES = ["Reshaely", "VanlyShan", "SolinXuan"]
    TOPIC = "修复星绒乐园的失控裂隙，探寻星绒本源的真相"
    STYLE = "治愈奇幻，细节丰富，多角色协作"

    # cat_world 框架文本中出现的核心关键词（用于断言框架已正确加载）
    FRAMEWORK_KEYWORDS = ["星绒乐园", "裂隙", "星绒能量"]
    # cat_world 主题关键词（用于断言最终故事与主题相关）
    TOPIC_KEYWORDS = ["星绒", "裂隙"]
    # persist_generated_role_slice 为角色视角文件添加的命名前缀（见 chroma_memory.py）。
    _ROLE_FILE_PREFIX = "chapter_"

    async def test_v030_full_pipeline(self):
        thread_id = f"v030_pipeline_{int(time.time())}"
        logger, log_path = create_run_logger()

        logger.info(f"[v0.3 TEST START] thread_id={thread_id}")
        logger.info(f"  story_id : {self.STORY_ID}")
        logger.info(f"  roles    : {self.ROLES}")
        logger.info(f"  topic    : {self.TOPIC}")
        logger.info(f"  Log file : {log_path}")

        state = build_input_state(
            story_id=self.STORY_ID,
            topic=self.TOPIC,
            style=self.STYLE,
            roles=self.ROLES,
            max_retry=1,
            rag_enabled=True,
            rag_top_k=4,
        )

        # ── 采集事件流 ────────────────────────────────────────────────────────
        nodes_completed: list[str] = []
        token_chars = 0

        # 各节点产物
        loaded_story_id = ""
        loaded_framework = ""
        role_assets: dict = {}
        rag_indexed_docs = -1
        role_mapping: dict = {}
        global_outline = ""
        established_facts = ""          # [v0.3]
        world_bible = ""                # [v0.3]
        rag_facts_indexed = -1          # [v0.3]
        role_story_identities: dict = {}
        rag_role_contexts: dict = {}    # [v0.3]
        role_view_drafts: dict = {}
        story_chapters: list = []       # [v0.3]
        integrated_draft = ""
        quality_status = ""
        quality_score = None
        final_story = ""
        run_id = None
        final_story_path = ""
        role_story_paths: dict = {}

        try:
            async for event in stream_story_events_async(state, thread_id=thread_id):
                etype = event.get("event")

                if etype == "node_start":
                    print(f"\n  [NODE-START] {event.get('node')}")

                elif etype == "token":
                    text = event.get("text") or ""
                    token_chars += len(text)
                    print(text, end="", flush=True)
                    # 仅在日志中记录非空内容，避免日志文件过于碎片化
                    if text.strip():
                        log_event(logger.name, text, level=10) # DEBUG level for tokens

                elif etype == "node_update":
                    node = event.get("node")
                    data = event.get("data", {})
                    nodes_completed.append(node)
                    logger.info(f"\n  [NODE-DONE]  {node}")

                    if node == "load_story_framework":
                        loaded_story_id = data.get("story_id", "")
                        loaded_framework = data.get("story_framework", "")
                        print(f"    framework_chars={len(loaded_framework)}, story_id={loaded_story_id}")

                    elif node == "load_roles":
                        role_assets = data.get("role_assets", {})
                        print(f"    roles loaded: {list(role_assets.keys())}")

                    elif node == "index_role_memories_for_rag":
                        rag_indexed_docs = data.get("rag_indexed_docs", -1)
                        print(f"    rag_indexed_docs={rag_indexed_docs}")

                    elif node == "map_roles_to_slots":
                        role_mapping = data.get("role_mapping", {})
                        print(f"    role_mapping keys={list(role_mapping.keys())}")

                    elif node == "plan_global_story":
                        global_outline = data.get("global_outline", "")
                        print(f"    global_outline_chars={len(global_outline)}")

                    elif node == "generate_established_facts":
                        established_facts = data.get("established_facts", "")
                        world_bible = data.get("world_bible", "")
                        print(f"    [v0.3] established_facts_chars={len(established_facts)}, "
                              f"world_bible_chars={len(world_bible)}")

                    elif node == "index_facts_for_rag":
                        rag_facts_indexed = data.get("rag_facts_indexed", -1)
                        print(f"    [v0.3] rag_facts_indexed={rag_facts_indexed}")

                    elif node == "adapt_roles_to_framework":
                        role_story_identities = data.get("role_story_identities", {})
                        print(f"    identities: {list(role_story_identities.keys())}")

                    elif node == "retrieve_role_rag_contexts":
                        rag_role_contexts = data.get("rag_role_contexts", {})
                        print(f"    [v0.3] rag_role_contexts keys={list(rag_role_contexts.keys())}")

                    elif node == "generate_role_views":
                        if data.get("role_view_drafts"):
                            role_view_drafts = data.get("role_view_drafts", {})
                            for rid, draft in role_view_drafts.items():
                                print(f"    draft[{rid}]_chars={len(draft or '')}")

                    elif node == "integrate_perspectives":
                        integrated_draft = data.get("integrated_draft", "")
                        story_chapters = data.get("story_chapters", [])
                        print(f"    [v0.3] story_chapters_count={len(story_chapters)}, "
                              f"integrated_draft_chars={len(integrated_draft)}")

                    elif node == "quality_check":
                        report = data.get("quality_report") or {}
                        quality_status = report.get("status", "")
                        quality_score = report.get("score")
                        print(f"    qa status={quality_status}, score={quality_score}")

                    elif node == "finalize_output":
                        final_story = data.get("final_story", "")
                        run_id = data.get("run_id")
                        final_story_path = data.get("final_story_path", "")
                        role_story_paths = data.get("role_story_paths", {})
                        print(f"    final_story_chars={len(final_story)}, run_id={run_id}")
                        print(f"    final_story_path={final_story_path}")

                elif etype == "error":
                    msg = event.get("message", "unknown error")
                    self.fail(f"[v0.3] 流程异常: {msg}")

                elif etype == "done":
                    print("\n  [DONE] 事件流结束")

        except Exception as exc:
            self.fail(f"[v0.3] 全流程执行异常: {exc}")

        # ════════════════════════════════════════════════════════════════════
        # Section 1: 节点链路完整性
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 节点链路完整性检查 | completed={nodes_completed}")

        # 验证所有必需节点均已完成
        for node in _REQUIRED_NODES_ORDERED:
            self.assertIn(
                node, nodes_completed,
                f"[链路断裂] 节点 '{node}' 未执行，流程不完整"
            )

        # 验证节点顺序：按预期顺序出现（相对顺序正确）
        last_idx = -1
        for node in _REQUIRED_NODES_ORDERED:
            try:
                idx = nodes_completed.index(node)
            except ValueError:
                continue  # 已在上面断言过存在性
            self.assertGreater(
                idx, last_idx,
                f"[节点顺序错误] '{node}' 应在前一个节点之后执行，实际顺序: {nodes_completed}"
            )
            last_idx = idx

        # Token 流量（证明 LLM 在正常生成）
        self.assertGreater(token_chars, _MIN_TOKEN_CHARS,
                           f"Token 流输出过少 ({token_chars})，LLM 可能未稳定生成")

        # ════════════════════════════════════════════════════════════════════
        # Section 2: 故事框架加载（load_story_framework）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 故事框架加载验证")
        self.assertEqual(loaded_story_id, self.STORY_ID,
                         f"加载的 story_id 与预期不符: {loaded_story_id!r}")
        self.assertTrue(loaded_framework.strip(),
                        "story_framework 为空，框架文件未成功读取")
        for kw in self.FRAMEWORK_KEYWORDS:
            self.assertIn(kw, loaded_framework,
                          f"框架文本缺少关键词 '{kw}'，可能读取了错误的框架文件")

        # ════════════════════════════════════════════════════════════════════
        # Section 3: 角色资产加载（load_roles）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 角色资产加载验证")
        self.assertEqual(set(role_assets.keys()), set(self.ROLES),
                         f"加载的角色集合与预期不符: {set(role_assets.keys())}")
        for rid in self.ROLES:
            profile = role_assets.get(rid, {}).get("profile", "")
            self.assertTrue(profile.strip(),
                            f"角色 {rid} 的 profile 为空，profile.md 可能缺失")

        # ════════════════════════════════════════════════════════════════════
        # Section 4: 角色记忆 RAG 索引（index_role_memories_for_rag）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 记忆 RAG 索引验证")
        self.assertGreaterEqual(rag_indexed_docs, 0,
                                "rag_indexed_docs 字段异常（负值）")

        # ════════════════════════════════════════════════════════════════════
        # Section 5: 角色槽位映射（map_roles_to_slots）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 角色槽位映射验证")
        self.assertTrue(role_mapping, "role_mapping 为空，LLM 映射可能失败")
        # 每个输入角色都应出现在映射的 key 中
        for rid in self.ROLES:
            self.assertTrue(
                any(rid in key for key in role_mapping.keys()),
                f"角色 {rid} 未出现在 role_mapping 中: {role_mapping}"
            )

        # ════════════════════════════════════════════════════════════════════
        # Section 6: 全局大纲规划（plan_global_story）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 全局大纲验证")
        self.assertTrue(global_outline.strip(), "global_outline 为空")
        outline_hits = [kw for kw in self.TOPIC_KEYWORDS if kw in global_outline]
        self.assertTrue(outline_hits,
                        f"global_outline 缺少主题关键词 {self.TOPIC_KEYWORDS}，大纲可能偏题")

        # ════════════════════════════════════════════════════════════════════
        # Section 7: [v0.3 核心] 既定事实提炼（generate_established_facts）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] [v0.3] 既定事实提炼验证")
        self.assertTrue(established_facts.strip(),
                        "[v0.3] established_facts 为空，generate_established_facts 节点未正确输出")

        # ════════════════════════════════════════════════════════════════════
        # Section 8: [v0.3 核心] 既定事实 RAG 索引（index_facts_for_rag）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] [v0.3] 既定事实 RAG 索引验证")
        self.assertGreaterEqual(rag_facts_indexed, 0,
                                "[v0.3] rag_facts_indexed 字段异常（负值）")

        # 验证既定事实物理文件已写入磁盘。
        from app.config import OPT_STORIES_DIR
        facts_dir = OPT_STORIES_DIR / self.STORY_ID / "facts"
        facts_file = facts_dir / f"facts_run{run_id}.md"
        self.assertTrue(facts_file.exists(),
                        f"[v0.3] 既定事实文件未落盘: {facts_file}")

        facts_content = facts_file.read_text(encoding="utf-8")
        self.assertIn("story_id:", facts_content,
                      "[v0.3] 既定事实文件缺少 story_id 头部信息")
        self.assertIn(self.STORY_ID, facts_content,
                      "[v0.3] 既定事实文件的 story_id 与预期不符")

        if world_bible.strip():
            world_file = facts_dir / f"world_run{run_id}.md"
            self.assertTrue(world_file.exists(),
                            f"[v0.3] world_bible 非空但文件未落盘: {world_file}")

        # ════════════════════════════════════════════════════════════════════
        # Section 9: 角色身份适配（adapt_roles_to_framework）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 角色身份适配验证")
        self.assertEqual(set(role_story_identities.keys()), set(self.ROLES),
                         f"role_story_identities 角色集合不完整: {set(role_story_identities.keys())}")
        for rid in self.ROLES:
            identity = role_story_identities.get(rid) or {}
            self.assertTrue(identity.get("story_name"),
                            f"角色 {rid} 的 story_name 为空")
            self.assertTrue(identity.get("story_personality_manifestation"),
                            f"角色 {rid} 的 story_personality_manifestation 为空")

        # ════════════════════════════════════════════════════════════════════
        # Section 10: [v0.3 核心] 混合 RAG 上下文检索（retrieve_role_rag_contexts）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] [v0.3] 混合 RAG 上下文检索验证")
        self.assertEqual(set(rag_role_contexts.keys()), set(self.ROLES),
                         f"[v0.3] rag_role_contexts 角色集合不完整: {set(rag_role_contexts.keys())}")
        # 每个角色的检索结果应为字符串（空字符串也可接受，但键必须存在）
        for rid in self.ROLES:
            ctx = rag_role_contexts.get(rid)
            self.assertIsInstance(ctx, str,
                                  f"[v0.3] 角色 {rid} 的 rag_role_context 类型异常: {type(ctx)}")

        # ════════════════════════════════════════════════════════════════════
        # Section 11: 角色视角草稿（generate_role_views）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 角色视角草稿验证")
        self.assertEqual(set(role_view_drafts.keys()), set(self.ROLES),
                         f"role_view_drafts 角色集合不完整: {set(role_view_drafts.keys())}")
        for rid in self.ROLES:
            draft = role_view_drafts.get(rid, "")
            self.assertGreaterEqual(
                len(draft.strip()), _MIN_ROLE_DRAFT_CHARS,
                f"角色 {rid} 草稿长度不足 {_MIN_ROLE_DRAFT_CHARS} 字 (实际: {len(draft.strip())})"
            )

        # ════════════════════════════════════════════════════════════════════
        # Section 12: [v0.3 核心] 章节化整合（integrate_perspectives）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] [v0.3] 章节化整合验证")
        self.assertTrue(integrated_draft.strip(), "integrated_draft 为空")
        self.assertIsInstance(story_chapters, list,
                              "[v0.3] story_chapters 应为列表类型")
        self.assertGreater(len(story_chapters), 0,
                           "[v0.3] story_chapters 列表为空，章节整合未生成任何章节")

        # ════════════════════════════════════════════════════════════════════
        # Section 13: 质检报告（quality_check）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 质检报告验证")
        self.assertIn(quality_status, {"PASS", "FAIL", ""},
                      f"quality_status 取值非法: {quality_status!r}")

        # ════════════════════════════════════════════════════════════════════
        # Section 14: 最终故事产物（finalize_output）
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 最终故事产物验证")
        self.assertTrue(final_story.strip(), "final_story 为空")
        self.assertIsNotNone(run_id, "run_id 为空，SQLite 持久化可能失败")
        self.assertTrue(final_story_path, "final_story_path 为空")
        self.assertTrue(role_story_paths, "role_story_paths 为空")

        # 文本质量指标
        metrics = _story_metrics(final_story)
        print(f"\n[METRICS] {metrics}")
        self.assertGreaterEqual(
            metrics["char_count"], _MIN_FINAL_CHARS,
            f"最终故事长度不足（需 >= {_MIN_FINAL_CHARS} 字，实际: {metrics['char_count']}）"
        )
        self.assertGreaterEqual(
            metrics["paragraph_count"], _MIN_PARAGRAPHS,
            f"段落数不足（需 >= {_MIN_PARAGRAPHS}，实际: {metrics['paragraph_count']}）"
        )
        self.assertGreaterEqual(
            metrics["sentence_count"], _MIN_SENTENCES,
            f"句子数不足（需 >= {_MIN_SENTENCES}，实际: {metrics['sentence_count']}）"
        )

        # 最终故事应包含主题关键词
        topic_hits = [kw for kw in self.TOPIC_KEYWORDS if kw in final_story]
        self.assertTrue(topic_hits,
                        f"最终故事缺少主题关键词 {self.TOPIC_KEYWORDS}，内容可能严重偏题")

        # ════════════════════════════════════════════════════════════════════
        # Section 15: 物理文件落盘验证
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] 物理文件落盘验证")

        # 最终故事文件
        final_path = Path(final_story_path)
        self.assertTrue(final_path.exists(),
                        f"最终故事文件不存在: {final_path}")
        self.assertEqual(final_path.parent.name, "final",
                         "最终故事文件应位于 .../final/ 目录")
        self.assertEqual(final_path.parent.parent.name, self.STORY_ID,
                         f"最终故事文件根目录应为故事名 '{self.STORY_ID}'")

        # 角色视角文件
        self.assertEqual(set(role_story_paths.keys()), set(self.ROLES),
                         f"role_story_paths 角色集合不完整: {set(role_story_paths.keys())}")
        for rid in self.ROLES:
            role_path = Path(role_story_paths[rid])
            self.assertTrue(role_path.exists(),
                            f"角色 {rid} 视角文件不存在: {role_path}")
            self.assertTrue(role_path.name.startswith(self._ROLE_FILE_PREFIX),
                            f"角色 {rid} 文件名命名规范错误，应以 '{self._ROLE_FILE_PREFIX}' 开头: {role_path.name}")
            self.assertEqual(role_path.parent.name, rid,
                             f"角色 {rid} 文件应位于对应角色目录下")
            self.assertEqual(role_path.parent.parent.name, self.STORY_ID,
                             f"角色 {rid} 文件根目录应为故事名 '{self.STORY_ID}'")

        # ════════════════════════════════════════════════════════════════════
        # Section 16: Checkpoint 持久化验证
        # ════════════════════════════════════════════════════════════════════
        print(f"\n[ASSERT] Checkpoint 持久化验证")
        history = await get_thread_history_async(thread_id)
        self.assertGreater(len(history), 0,
                           "线程历史为空，LangGraph checkpoint 持久化可能失败")

        # ════════════════════════════════════════════════════════════════════
        print(
            f"\n[v0.3 TEST SUCCESS] "
            f"nodes={len(nodes_completed)}, "
            f"chars={metrics['char_count']}, "
            f"paragraphs={metrics['paragraph_count']}, "
            f"story_chapters={len(story_chapters)}, "
            f"rag_facts_indexed={rag_facts_indexed}, "
            f"qa={quality_status}:{quality_score}"
        )


if __name__ == "__main__":
    unittest.main()
