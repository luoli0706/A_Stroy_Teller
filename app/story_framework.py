from pathlib import Path


DEFAULT_STORY_ID = "default"
DEFAULT_STORIES_DIR = Path("stories")


def load_story_framework(
    story_id: str,
    stories_dir: str | Path = DEFAULT_STORIES_DIR,
) -> tuple[str, str]:
    root = Path(stories_dir)
    selected_id = (story_id or DEFAULT_STORY_ID).strip() or DEFAULT_STORY_ID

    selected_path = root / selected_id / "framework.md"
    default_path = root / DEFAULT_STORY_ID / "framework.md"

    if selected_path.exists():
        return selected_id, selected_path.read_text(encoding="utf-8").strip()

    if default_path.exists():
        return DEFAULT_STORY_ID, default_path.read_text(encoding="utf-8").strip()

    fallback = (
        "# Minimal Framework\n"
        "- Three-act structure\n"
        "- Keep shared facts consistent across roles\n"
        "- End with a clear resolution"
    )
    return DEFAULT_STORY_ID, fallback
