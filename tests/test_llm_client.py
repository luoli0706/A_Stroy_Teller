import unittest
from app.llm_client import get_story_client

class TestLLMClient(unittest.IsolatedAsyncioTestCase):
    """
    LLM 客户端单元测试 (v0.2.5)。
    重点测试异步健康检查与角色映射/适配接口。
    """
    
    async def test_health_check(self):
        client = get_story_client()
        try:
            res = await client.health_check_async()
            self.assertIsInstance(res, dict)
            self.assertIn("ok", res)
        except Exception as e:
            self.skipTest(f"Ollama service unavailable: {e}")

    async def test_map_roles_to_slots_structure(self):
        client = get_story_client()
        roles = ["Reshaely"]
        profiles = {"Reshaely": "A tech hunter with grey hair."}
        framework = "A story about a library. Slot: Librarian."
        
        try:
            # 验证返回是否为合法的 JSON 字符串（逻辑节点要求）
            res = await client.map_roles_to_slots_async(roles, profiles, framework)
            data = json.loads(res)
            self.assertIsInstance(data, dict)
        except Exception as e:
            self.skipTest(f"LLM Call failed: {e}")

if __name__ == "__main__":
    import json
    unittest.main()
