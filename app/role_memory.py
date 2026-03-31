from pathlib import Path

from app.state import RoleAsset


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_role_assets(base_dir: str | Path, roles: list[str]) -> dict[str, RoleAsset]:
    role_root = Path(base_dir)
    assets: dict[str, RoleAsset] = {}

    for role_id in roles:
        role_dir = role_root / role_id
        assets[role_id] = {
            "profile": _read_text_if_exists(role_dir / "profile.md"),
            "memory": _read_text_if_exists(role_dir / "memory.md"),
        }

    return assets


def discover_roles(base_dir: str | Path) -> list[str]:
    role_root = Path(base_dir)
    if not role_root.exists():
        return []

    return sorted(
        child.name
        for child in role_root.iterdir()
        if child.is_dir()
    )
