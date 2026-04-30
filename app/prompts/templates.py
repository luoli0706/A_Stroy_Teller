"""Prompt 模板 —— 从 StoryLLMClient 方法中提取。"""


def casting_director_prompt(profiles_summary: str, framework: str) -> str:
    return (
        "You are a casting director. Assign each Actor to a Role Slot from the framework.\n"
        f"Actors:\n{profiles_summary}\n\n"
        f"Story Framework:\n{framework}\n\n"
        "Return a JSON object where keys are Actor IDs and values are Slot Names.\n"
        "If an actor doesn't fit any slot, assign them as 'New Character: [Proposed Role Name]'."
    )


def story_planner_prompt(
    topic: str, style: str, mapping_str: str, framework: str
) -> str:
    return (
        "You are a story planner. Build a concise 3-act outline with timeline beats. "
        f"Topic: {topic}\nStyle: {style}\n\n"
        f"Cast Assignment:\n{mapping_str}\n\n"
        f"Story framework:\n{framework}\n\n"
        "Output format:\n- Act 1\n- Act 2\n- Act 3\n- Shared facts"
    )


def relationship_matrix_prompt(ids_summary: str) -> str:
    return (
        "Generate a social relationship matrix for these characters in the current story.\n"
        f"Cast:\n{ids_summary}\n\n"
        "Describe the initial attitude, conflict, or bond between each pair."
    )


def role_adaptation_prompt(
    generic_profile: str, framework: str, outline: str
) -> str:
    return (
        "You are an actor preparing for a role. CRITICAL: Your core personality must remain consistent.\n"
        f"Your Real Identity (Generic Profile):\n{generic_profile}\n\n"
        f"Story Framework:\n{framework}\n\n"
        f"Global Outline:\n{outline}\n\n"
        "TASK: Generate your 'Temporary Story Identity'. Ensure your traits manifest authentically in this new context.\n"
        "Output Format (JSON): {'story_name', 'story_personality_manifestation', 'story_specific_goal', 'story_key_items'}"
    )


def established_facts_prompt(
    topic: str, style: str, mapping_str: str, global_outline: str
) -> str:
    return (
        "You are a story bible writer. Based on the global outline, extract two structured sections:\n\n"
        "## ESTABLISHED FACTS (既定事实)\n"
        "List all key story events as objective facts in chronological order. "
        "Each fact should be a concise statement of WHAT happened, WHEN, WHERE, and WHO was involved. "
        "These are the authoritative ground-truth events that ALL characters must agree on.\n"
        "Format: [Timestamp/Chapter] Fact description\n\n"
        "## WORLD BIBLE (世界观设定)\n"
        "Describe the story world: setting, rules, atmosphere, and any special lore relevant to this story.\n\n"
        f"Topic: {topic}\nStyle: {style}\n\n"
        f"Cast:\n{mapping_str}\n\n"
        f"Global Outline:\n{global_outline}\n\n"
        "Output both sections clearly labeled."
    )


def role_view_prompt(
    generic_profile: str,
    story_identity: str,
    relationships: str,
    style: str,
    outline: str,
    memory: str,
    rag_context: str,
) -> str:
    return (
        "You are writing one role-specific narrative in first person. "
        f"REAL IDENTITY (DO NOT BREAK CHARACTER):\n{generic_profile}\n"
        f"STORY IDENTITY:\n{story_identity}\n"
        f"RELATIONSHIPS:\n{relationships}\n\n"
        f"Style: {style}\nGlobal outline:\n{outline}\n\n"
        f"Past Memories:\n{memory}\n"
        "ESTABLISHED FACTS & WORLD BIBLE (authoritative ground truth — "
        "your narrative must respect these facts; add subjective detail and emotion, "
        "but do NOT contradict any listed fact):\n"
        f"{rag_context or '(none)'}\n\n"
        "Output: Perspective Summary, Scene Narrative, Role-specific interpretation"
    )


def integrate_simple_prompt(
    topic: str, style: str, draft_blocks: str
) -> str:
    return (
        "Merge multi-role narratives into one coherent story. "
        f"Topic: {topic}\nStyle: {style}\n\nRole drafts:\n{draft_blocks}\n\n"
        "Output: Title, Final integrated story"
    )


def integrate_chapter_prompt(
    idx: int,
    topic: str,
    style: str,
    chapter_facts: str,
    draft_blocks: str,
) -> str:
    return (
        f"You are merging multi-role narratives for Chapter {idx} of the story.\n"
        f"Topic: {topic}\nStyle: {style}\n\n"
        f"Chapter {idx} Established Facts (ground truth, must be respected):\n{chapter_facts}\n\n"
        f"Role drafts (use relevant sections only):\n{draft_blocks}\n\n"
        f"Output: A cohesive Chapter {idx} narrative that:\n"
        "- Aligns all character actions with the established facts\n"
        "- Preserves each character's voice and perspective\n"
        "- Resolves any conflicts by deferring to established facts\n"
        "- Keeps the designated style throughout"
    )


def quality_check_prompt(
    role_ids: str, outline: str, integrated_story: str
) -> str:
    return (
        "Evaluate story consistency. Return ONLY a JSON object with fields: "
        "'status' (PASS/FAIL), 'score' (0-10), 'conflicts' (list of strings), 'suggestions' (list).\n\n"
        f"Roles: {role_ids}\nOutline:\n{outline}\n\nStory:\n{integrated_story}"
    )
