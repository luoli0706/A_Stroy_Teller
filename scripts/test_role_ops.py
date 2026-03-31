import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.role_memory import (
    add_role_memory_slice,
    add_role_profile,
    delete_all_role_memories,
    delete_role_profile,
)


ROLE_PROFILES = {
    "Reshaely": """# Reshaely (罹小璃) Profile

- 中文名: 罹小璃
- Persona: 沉迷游戏的美少女
- Voice: 轻快、俏皮、带一点游戏术语
- Goal: 在现实谜团中找到像解谜游戏一样的隐藏线索
- Weakness: 容易把现实当成游戏关卡而忽略风险
""",
    "VanlyShan": """# VanlyShan (万离珊) Profile

- 中文名: 万离珊
- Persona: 侦探助手
- Voice: 冷静、务实、擅长记录
- Goal: 协助宋林萱收集证据并校验细节
- Weakness: 过于谨慎，可能错失快速行动窗口
""",
    "SolinXuan": """# SolinXuan (宋林萱) Profile

- 中文名: 宋林萱
- Persona: 少女侦探
- Voice: 逻辑严谨、推理导向、观察细腻
- Goal: 还原案件真相并保护关键证人
- Weakness: 过度投入推理时会忽略自身安全
""",
}


ROLE_MEMORIES = {
    "Reshaely": {
        "case_library_midnight": "- 在图书馆后门看见过一个戴耳机的人影。\n- 她记得地板有像游戏机关一样的压力板声。",
        "case_clocktower_signal": "- 她在游戏论坛上见过类似钟楼符号。\n- 认为信号图案可能是关卡密码。",
    },
    "VanlyShan": {
        "case_library_midnight": "- 记录了封存书架附近的灰尘断层。\n- 证物袋编号与入库时间已经同步。",
        "case_clocktower_signal": "- 复核了钟楼附近两处脚印尺寸。\n- 初步排除同一人往返作案的可能。",
    },
    "SolinXuan": {
        "case_library_midnight": "- 推断作案窗口在 22:10 至 22:25。\n- 关键矛盾点在于门锁无撬动但藏书缺失。",
        "case_clocktower_signal": "- 确认钟楼符号与旧案卷宗的标记一致。\n- 下一步需要追踪曾接触卷宗的人员名单。",
    },
}


def main() -> None:
    print("[1/3] Delete test roles: alice, bob")
    for role_id in ["alice", "bob"]:
        profile_deleted = delete_role_profile(role_id)
        memory_deleted_count = delete_all_role_memories(role_id)
        print(
            f"- {role_id}: profile_deleted={profile_deleted}, memory_slices_deleted={memory_deleted_count}"
        )

    print("[2/3] Add new role profiles")
    for role_id, profile_text in ROLE_PROFILES.items():
        profile_path = add_role_profile(role_id, profile_text)
        print(f"- profile created: {profile_path}")

    print("[3/3] Add memory slices for each role")
    for role_id, story_slices in ROLE_MEMORIES.items():
        for story_id, memory_text in story_slices.items():
            memory_path = add_role_memory_slice(role_id, story_id, memory_text)
            print(f"- memory slice created: {memory_path}")

    print("Role operation test completed.")


if __name__ == "__main__":
    main()
