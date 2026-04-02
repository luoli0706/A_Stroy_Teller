import unittest
from app.llm_client import get_story_client

class TestLLMClient(unittest.IsolatedAsyncioTestCase):
    async def test_health_check(self):
        client = get_story_client()
        # 注意：此测试依赖于本地 Ollama 是否运行
        # 我们仅检查返回结构是否正确
        try:
            res = await client.health_check_async()
            self.assertIn("ok", res)
            self.assertIn("message", res)
        except Exception:
            self.skipTest("Ollama service not available for testing")

    async def test_singleton(self):
        c1 = get_story_client()
        c2 = get_story_client()
        self.assertIs(c1, c2)

if __name__ == "__main__":
    unittest.main()
