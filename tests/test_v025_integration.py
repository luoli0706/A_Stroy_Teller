import asyncio
import unittest
import json
import os
from app.runtime import build_input_state, stream_story_events_async, get_thread_history_async
from app.state import StoryState

class TestV025Integration(unittest.IsolatedAsyncioTestCase):
    """
    针对 v0.2.5 的全自动集成测试。
    支持捕获 astream_events，实时输出模型 Token。
    """

    async def test_ice_wind_persistence_flow(self):
        import time
        thread_id = f"auto_test_{int(time.time())}"
        roles = ["Reshaely", "VanlyShan"] 
        topic = "寻找冰原上的信号塔"
        style = "mysterious"
        
        print(f"\n🚀 [START] 全自动集成测试启动 | Thread ID: {thread_id}")
        
        state = build_input_state(
            story_id="Travel_with_ice_and_wind",
            topic=topic,
            style=style,
            roles=roles,
            max_retry=1
        )

        print("逐步监控异步事件流...")
        nodes_completed = []
        final_story_received = False

        try:
            async for event in stream_story_events_async(state, thread_id=thread_id):
                etype = event.get("event")
                
                if etype == "node_start":
                    print(f"\n⏳ 正在启动节点: [{event.get('node')}]")
                
                elif etype == "token":
                    # 实时输出 Token，证明模型在运行
                    print(event.get("text"), end="", flush=True)
                
                elif etype == "node_update":
                    node = event.get("node")
                    data = event.get("data", {})
                    print(f"\n✅ 节点完成: {node}")
                    nodes_completed.append(node)
                    
                    if node == "finalize_output":
                        if data.get("final_story"):
                            final_story_received = True
                            print(f"\n📖 故事生成完毕，长度: {len(data['final_story'])} 字")
                
                elif etype == "error":
                    error_msg = event.get("message")
                    print(f"\n❌ 流程异常: {error_msg}")
                    self.fail(f"Flow interrupted by error: {error_msg}")
                
                elif etype == "done":
                    print("\n🏁 [FINISH] 执行结束。")

            # 结果完整性验证
            self.assertTrue(len(nodes_completed) > 5, "执行节点数量过少")
            
            print("\n正在验证数据库持久化记录...")
            history = await get_thread_history_async(thread_id)
            self.assertGreater(len(history), 0)
            print(f"🎊 [SUCCESS] 测试通过。")
            
        except Exception as e:
            print(f"\n🔥 [CRASH] 测试异常: {str(e)}")
            self.fail(f"Full flow failed with error: {str(e)}")

if __name__ == "__main__":
    unittest.main()
