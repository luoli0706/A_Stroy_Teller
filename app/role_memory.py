import shutil
from pathlib import Path
from app.config import ROLE_DIR, MEMORY_DIR

def discover_roles(role_dir: str = str(ROLE_DIR)) -> list[str]:
    """发现所有可用的角色。"""
    root = Path(role_dir)
    if not root.exists():
        return []
    return sorted([d.name for d in root.iterdir() if d.is_dir()])

def load_role_assets(role_dir: str, roles: list[str], memory_dir: str) -> dict[str, dict]:
    """加载指定角色的设定与（预览版）记忆。"""
    assets = {}
    for rid in roles:
        profile_path = Path(role_dir) / rid / "profile.md"
        # 尝试从角色目录或记忆根目录查找记忆汇总文件
        memory_path = Path(memory_dir) / rid / f"{rid}_summary.md" # 这里使用 Alpha 0.1 定义的汇总
        
        profile_text = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
        memory_text = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
        
        assets[rid] = {"profile": profile_text, "memory": memory_text}
    return assets

def add_role_profile(role_id: str, content: str) -> str:
    path = ROLE_DIR / role_id
    path.mkdir(parents=True, exist_ok=True)
    f = path / "profile.md"
    f.write_text(content, encoding="utf-8")
    return str(f)

def delete_role_profile(role_id: str) -> bool:
    path = ROLE_DIR / role_id
    if path.exists():
        shutil.rmtree(path)
        return True
    return False

def add_role_memory_slice(role_id: str, story_id: str, content: str) -> str:
    path = MEMORY_DIR / role_id
    path.mkdir(parents=True, exist_ok=True)
    f = path / f"{story_id}.md"
    f.write_text(content, encoding="utf-8")
    return str(f)
