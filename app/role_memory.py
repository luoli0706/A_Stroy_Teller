import re
import shutil
from pathlib import Path
from app.config import ROLE_DIR, MEMORY_DIR

# 安全的 role_id / story_id 格式：字母数字开头，仅允许字母数字、连字符、下划线、点号
_SAFE_ID_RE = re.compile(r'^[a-zA-Z0-9_][-a-zA-Z0-9_.]{0,63}$')


def _validate_id(value: str, label: str = "id") -> str:
    """校验标识符，防止路径遍历注入。"""
    value = value.strip()
    if not _SAFE_ID_RE.match(value):
        raise ValueError(
            f"Invalid {label}: {value!r}. "
            f"Must match pattern: letters/digits/underscore, max 64 chars, no path separators."
        )
    if ".." in value or "/" in value or "\\" in value:
        raise ValueError(f"{label} contains path separator: {value!r}")
    return value


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
        _validate_id(rid, "role_id")
        profile_path = Path(role_dir) / rid / "profile.md"
        memory_path = Path(memory_dir) / rid / f"{rid}_summary.md"

        profile_text = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
        memory_text = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""

        assets[rid] = {"profile": profile_text, "memory": memory_text}
    return assets


def add_role_profile(role_id: str, content: str) -> str:
    _validate_id(role_id, "role_id")
    path = ROLE_DIR / role_id
    path.mkdir(parents=True, exist_ok=True)
    f = path / "profile.md"
    f.write_text(content, encoding="utf-8")
    return str(f)


def delete_role_profile(role_id: str) -> bool:
    _validate_id(role_id, "role_id")
    path = ROLE_DIR / role_id
    if path.exists():
        shutil.rmtree(path)
        return True
    return False


def add_role_memory_slice(role_id: str, story_id: str, content: str) -> str:
    _validate_id(role_id, "role_id")
    _validate_id(story_id, "story_id")
    path = MEMORY_DIR / role_id
    path.mkdir(parents=True, exist_ok=True)
    f = path / f"{story_id}.md"
    f.write_text(content, encoding="utf-8")
    return str(f)
