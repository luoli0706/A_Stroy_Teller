import asyncio
import unittest
import json
from app.runtime import build_input_state, run_story_async
from app.state import StoryState

class TestIceAndWindFlow(unittest.IsolatedAsyncioTestCase):
    """
    针对 v0.2.3 的集成测试：使用三个演员入驻《冰与风之行》框架。
    验证点：
    1. 角色映射 (Role Mapping) 是否生成。
    2. 身份适配 (Identity Adaptation) 是否生成。
    3. 关系网 (Relationships) 是否生成。
    4. 最终故事生成。
    """

    async def test_full_flow_ice_wind(self):
        # 1. 准备输入状态
        roles = ["Reshaely", "VanlyShan", "SolinXuan"]
        topic = "寻找失落的恒定之火"
        style = "epic and cold"
        story_id = "Travel_with_ice_and_wind"
        
        state = build_input_state(
            story_id=story_id,
            topic=topic,
            style=style,
            roles=roles,
            max_retry=1
        )

        # 2. 执行 Graph (由于依赖 Ollama，可能需要较长时间)
        print(f"\nStarting test_full_flow_ice_wind with roles: {roles}")
        try:
            result = await run_story_async(state)
            
            # 3. 验证结果
            self.assertIn("final_story", result)
            self.assertIn("role_mapping", result)
            self.assertIn("role_story_identities", result)
            self.assertIn("relationship_matrix", result)
            
            # 验证角色映射是否覆盖了所有角色
            mapping = result["role_mapping"]
            for r in roles:
                self.assertTrue(any(r in key for key in mapping.keys()), f"Role {r} missing from mapping")

            # 验证身份适配模型结构
            identities = result["role_story_identities"]
            for r in roles:
                self.assertIn(r, identities)
                # 检查 Pydantic 转换后的字典字段
                self.assertIn("story_name", identities[r])
                self.assertIn("story_personality_manifestation", identities[r])

            print("Test successful! Relationship Matrix Preview:")
            print(result["relationship_matrix"][:200] + "...")
            
        except Exception as e:
            self.fail(f"Full flow failed with error: {str(e)}")

if __name__ == "__main__":
    unittest.main()
