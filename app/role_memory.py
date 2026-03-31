from pathlib import Path

from app.state import RoleAsset


DEFAULT_ROLE_DIR = Path("role")
DEFAULT_MEMORY_DIR = Path("memory")


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _normalize_story_id(story_id: str) -> str:
    value = story_id.strip()
    if not value:
        return "default"
    return value.replace(" ", "_")


def add_role_profile(
    role_id: str,
    profile_text: str,
    role_dir: str | Path = DEFAULT_ROLE_DIR,
) -> Path:
    role_path = Path(role_dir) / role_id
    role_path.mkdir(parents=True, exist_ok=True)
    profile_path = role_path / "profile.md"
    profile_path.write_text(profile_text.strip() + "\n", encoding="utf-8")
    return profile_path


def delete_role_profile(
    role_id: str,
    role_dir: str | Path = DEFAULT_ROLE_DIR,
) -> bool:
    role_path = Path(role_dir) / role_id
    profile_path = role_path / "profile.md"
    if not profile_path.exists():
        return False

    profile_path.unlink()
    if role_path.exists() and not any(role_path.iterdir()):
        role_path.rmdir()
    return True


def add_role_memory_slice(
    role_id: str,
    story_id: str,
    memory_text: str,
    memory_dir: str | Path = DEFAULT_MEMORY_DIR,
) -> Path:
    role_memory_path = Path(memory_dir) / role_id
    role_memory_path.mkdir(parents=True, exist_ok=True)
    memory_path = role_memory_path / f"{_normalize_story_id(story_id)}.md"
    memory_path.write_text(memory_text.strip() + "\n", encoding="utf-8")
    return memory_path


def delete_role_memory_slice(
    role_id: str,
    story_id: str,
    memory_dir: str | Path = DEFAULT_MEMORY_DIR,
) -> bool:
    memory_path = Path(memory_dir) / role_id / f"{_normalize_story_id(story_id)}.md"
    if not memory_path.exists():
        return False

    memory_path.unlink()
    parent_dir = memory_path.parent
    if parent_dir.exists() and not any(parent_dir.iterdir()):
        parent_dir.rmdir()
    return True


def delete_all_role_memories(
    role_id: str,
    memory_dir: str | Path = DEFAULT_MEMORY_DIR,
    role_dir: str | Path = DEFAULT_ROLE_DIR,
) -> int:
    role_memory_path = Path(memory_dir) / role_id
    deleted = 0

    if role_memory_path.exists():
        for memory_file in role_memory_path.glob("*.md"):
            memory_file.unlink()
            deleted += 1

        if role_memory_path.exists() and not any(role_memory_path.iterdir()):
            role_memory_path.rmdir()

    # Backward compatibility: remove legacy role/<id>/memory.md.
    legacy_memory_path = Path(role_dir) / role_id / "memory.md"
    if legacy_memory_path.exists():
        legacy_memory_path.unlink()
        deleted += 1

    role_path = Path(role_dir) / role_id
    if role_path.exists() and not any(role_path.iterdir()):
        role_path.rmdir()

    return deleted


def _load_role_memory(role_id: str, memory_dir: Path) -> str:
    role_memory_path = memory_dir / role_id
    if not role_memory_path.exists():
        return ""

    slices: list[str] = []
    for memory_file in sorted(role_memory_path.glob("*.md")):
        content = _read_text_if_exists(memory_file)
        if content:
            slices.append(f"# Slice: {memory_file.stem}\n{content}")

    return "\n\n".join(slices).strip()


def load_role_assets(
    base_dir: str | Path,
    roles: list[str],
    memory_dir: str | Path = DEFAULT_MEMORY_DIR,
) -> dict[str, RoleAsset]:
    role_root = Path(base_dir)
    memory_root = Path(memory_dir)
    assets: dict[str, RoleAsset] = {}

    for role_id in roles:
        role_dir = role_root / role_id
        assets[role_id] = {
            "profile": _read_text_if_exists(role_dir / "profile.md"),
            "memory": _load_role_memory(role_id, memory_root),
        }

    return assets


def discover_roles(base_dir: str | Path) -> list[str]:
    role_root = Path(base_dir)
    if not role_root.exists():
        return []

    return sorted(
        child.name
        for child in role_root.iterdir()
        if child.is_dir() and (child / "profile.md").exists()
    )
