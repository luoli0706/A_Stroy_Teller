import os
import time
import unittest
from pathlib import Path

from app.runtime import build_input_state, get_thread_history_async, stream_story_events_async


def _compute_story_metrics(text: str) -> dict:
    cleaned = (text or "").strip()
    paragraphs = [line.strip() for line in cleaned.splitlines() if line.strip()]
    sentence_marks = "。！？!?；;"
    sentence_count = sum(cleaned.count(mark) for mark in sentence_marks)
    char_count = len(cleaned)
    avg_paragraph_chars = int(char_count / max(len(paragraphs), 1))
    return {
        "char_count": char_count,
        "paragraph_count": len(paragraphs),
        "sentence_count": sentence_count,
        "avg_paragraph_chars": avg_paragraph_chars,
    }


class TestV026CatWorldLongText(unittest.IsolatedAsyncioTestCase):
    """
    v0.2.6 集成测试：cat_world 三角色长文本评估。

    BREAK: 本用例用于验证结构性落盘改造后的完整链路，不作为稳定回归基线。

    目标：
    1) 复用 v0.2.5 的异步事件流路径验证节点执行稳定性。
    2) 使用三角色并发生成，验证角色草稿完整性。
    3) 对最终文本执行长文本指标评估（长度、段落、句子）。
    """

    async def test_cat_world_three_roles_long_story(self):
        thread_id = f"cat_world_long_text_{int(time.time())}"
        roles = ["Reshaely", "VanlyShan", "SolinXuan"]
        topic = "在星绒乐园修复失控裂隙，并揭示星绒本源的真相"
        style = "治愈奇幻，偏长篇，细节丰富，多角色协作"

        min_final_story_chars = int(os.getenv("TEST_MIN_FINAL_STORY_CHARS", "1800"))
        min_role_draft_chars = int(os.getenv("TEST_MIN_ROLE_DRAFT_CHARS", "350"))
        min_paragraphs = int(os.getenv("TEST_MIN_STORY_PARAGRAPHS", "6"))
        min_sentences = int(os.getenv("TEST_MIN_STORY_SENTENCES", "18"))

        print(f"\n[START] cat_world 长文本集成测试 | thread_id={thread_id}")
        print(f"[CONFIG] roles={roles}")

        state = build_input_state(
            story_id="cat_world",
            topic=topic,
            style=style,
            roles=roles,
            max_retry=1,
            rag_enabled=True,
            rag_top_k=4,
        )

        nodes_completed = []
        token_chars = 0
        final_story = ""
        role_view_drafts = {}
        quality_status = ""
        quality_score = None
        run_id = None
        final_story_path = ""
        role_story_paths = {}
        loaded_story_id = ""
        loaded_framework = ""
        global_outline = ""

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
                    node = event.get("node")
                    data = event.get("data", {})
                    nodes_completed.append(node)
                    print(f"\n[NODE-DONE] {node}")

                    if node == "load_story_framework":
                        loaded_story_id = data.get("story_id", "")
                        loaded_framework = data.get("story_framework", "")
                        print(
                            f"[FRAMEWORK] story_id={loaded_story_id}, "
                            f"framework_chars={len(loaded_framework)}"
                        )

                    if node == "plan_global_story":
                        global_outline = data.get("global_outline", "")

                    if node == "generate_role_views" and data.get("role_view_drafts"):
                        role_view_drafts = data.get("role_view_drafts", {})

                    if node == "quality_check" and data.get("quality_report"):
                        report = data.get("quality_report", {})
                        quality_status = report.get("status", "")
                        quality_score = report.get("score")
                        print(f"[QA] status={quality_status}, score={quality_score}")

                    if node == "finalize_output":
                        final_story = data.get("final_story", "")
                        run_id = data.get("run_id")
                        final_story_path = data.get("final_story_path", "")
                        role_story_paths = data.get("role_story_paths", {})
                        print(f"[FINALIZE] final_story_chars={len(final_story)}, run_id={run_id}")

                elif etype == "error":
                    message = event.get("message", "unknown error")
                    self.fail(f"Flow interrupted by error: {message}")

                elif etype == "done":
                    print("\n[DONE] 事件流结束")

            self.assertGreater(len(nodes_completed), 8, "执行节点数量过少，流程可能未完整运行")
            self.assertGreater(token_chars, 300, "Token 流输出过少，模型可能未稳定生成")
            self.assertIn("load_story_framework", nodes_completed, "未执行框架加载节点")

            # 显式确认读取了 stories/cat_world/framework.md 对应内容
            self.assertEqual(loaded_story_id, "cat_world", "框架加载并非 cat_world")
            self.assertTrue(loaded_framework.strip(), "story_framework 为空，未读取框架文本")
            self.assertIn("星绒乐园", loaded_framework, "加载的框架文本不符合 cat_world 预期")

            self.assertTrue(final_story.strip(), "final_story 为空")
            self.assertIsNotNone(run_id, "run_id 未返回，持久化可能未完成")
            self.assertTrue(final_story_path, "final_story_path 未返回")
            self.assertTrue(role_story_paths, "role_story_paths 未返回")

            self.assertTrue(global_outline.strip(), "global_outline 为空")

            self.assertEqual(set(role_view_drafts.keys()), set(roles), "角色草稿集合与输入角色不一致")
            for role_id in roles:
                draft = role_view_drafts.get(role_id, "")
                self.assertGreaterEqual(
                    len(draft.strip()),
                    min_role_draft_chars,
                    f"角色 {role_id} 草稿长度不足，未达到长文本生成预期",
                )

            metrics = _compute_story_metrics(final_story)
            print(f"\n[METRICS] {metrics}")

            self.assertGreaterEqual(
                metrics["char_count"],
                min_final_story_chars,
                f"最终故事长度不足，需 >= {min_final_story_chars} 字",
            )
            self.assertGreaterEqual(
                metrics["paragraph_count"],
                min_paragraphs,
                f"段落数量不足，需 >= {min_paragraphs}",
            )
            self.assertGreaterEqual(
                metrics["sentence_count"],
                min_sentences,
                f"句子数量不足，需 >= {min_sentences}",
            )

            outline_keyword_hits = [kw for kw in ["星绒", "乐园", "裂隙"] if kw in global_outline]
            self.assertTrue(outline_keyword_hits, "global_outline 缺少 cat_world 核心语义，可能未充分利用框架")

            # 对框架语义做最小锚定，避免生成内容完全偏题
            keyword_hits = [kw for kw in ["星绒", "乐园", "裂隙"] if kw in final_story]
            self.assertTrue(keyword_hits, "最终故事缺少 cat_world 核心语义关键词")

            history = await get_thread_history_async(thread_id)
            self.assertGreater(len(history), 0, "线程历史为空，checkpoint 持久化可能失败")

            final_path = Path(final_story_path)
            self.assertTrue(final_path.exists(), f"最终文件不存在: {final_path}")
            self.assertEqual(final_path.parent.name, "final", "最终文件未落在 final 目录")

            story_root = final_path.parent.parent
            self.assertEqual(story_root.name, "cat_world", "最终文件根目录不是目标故事名")

            for role_id in roles:
                role_path_str = role_story_paths.get(role_id, "")
                self.assertTrue(role_path_str, f"角色 {role_id} 的输出路径缺失")
                role_path = Path(role_path_str)
                self.assertTrue(role_path.exists(), f"角色文件不存在: {role_path}")
                self.assertEqual(role_path.parent.name, role_id, f"角色 {role_id} 文件未落在对应角色目录")
                self.assertEqual(role_path.parent.parent.name, "cat_world", f"角色 {role_id} 文件根目录不是故事名")
                self.assertTrue(role_path.name.startswith("chapter_"), f"角色 {role_id} 文件名不符合篇章命名")

            # 质检结果不强制 PASS，但要求字段存在，便于后续趋势分析
            self.assertTrue(
                quality_status in {"PASS", "FAIL", ""},
                f"quality_status 非法: {quality_status}",
            )

            print(
                f"[SUCCESS] 长文本测试通过 | chars={metrics['char_count']} | "
                f"paragraphs={metrics['paragraph_count']} | qa={quality_status}:{quality_score}"
            )

        except Exception as exc:
            print(f"\n[CRASH] {exc}")
            self.fail(f"cat_world long-text integration failed: {exc}")


if __name__ == "__main__":
    unittest.main()