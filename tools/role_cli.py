import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.role_memory import (  # noqa: E402
    add_role_memory_slice,
    add_role_profile,
    delete_all_role_memories,
    delete_role_memory_slice,
    delete_role_profile,
    discover_roles,
)


def _read_text_arg(text: str | None, file_path: str | None) -> str:
    if text is not None:
        return text
    if file_path is not None:
        return Path(file_path).read_text(encoding="utf-8")
    raise ValueError("Provide either --text or --file")


def cmd_add_profile(args: argparse.Namespace) -> int:
    profile_text = _read_text_arg(args.text, args.file)
    path = add_role_profile(args.role_id, profile_text, role_dir=args.role_dir)
    print(f"Profile saved: {path}")
    return 0


def cmd_delete_profile(args: argparse.Namespace) -> int:
    deleted = delete_role_profile(args.role_id, role_dir=args.role_dir)
    print(f"Profile deleted: {deleted}")
    return 0


def cmd_add_memory(args: argparse.Namespace) -> int:
    memory_text = _read_text_arg(args.text, args.file)
    path = add_role_memory_slice(
        args.role_id,
        args.story_id,
        memory_text,
        memory_dir=args.memory_dir,
    )
    print(f"Memory slice saved: {path}")
    return 0


def cmd_delete_memory(args: argparse.Namespace) -> int:
    deleted = delete_role_memory_slice(
        args.role_id,
        args.story_id,
        memory_dir=args.memory_dir,
    )
    print(f"Memory slice deleted: {deleted}")
    return 0


def cmd_delete_all_memory(args: argparse.Namespace) -> int:
    deleted_count = delete_all_role_memories(
        args.role_id,
        memory_dir=args.memory_dir,
        role_dir=args.role_dir,
    )
    print(f"Deleted memory slices: {deleted_count}")
    return 0


def cmd_list_roles(args: argparse.Namespace) -> int:
    roles = discover_roles(args.role_dir)
    if not roles:
        print("No roles found.")
        return 0

    print("Roles:")
    for role_id in roles:
        print(f"- {role_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="role-cli",
        description="Role profile and memory management CLI",
    )
    parser.add_argument("--role-dir", default="role", help="Role profile directory")
    parser.add_argument("--memory-dir", default="memory", help="Role memory directory")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_add_profile = subparsers.add_parser("add-profile", help="Add or update role profile")
    p_add_profile.add_argument("role_id")
    p_add_profile.add_argument("--text")
    p_add_profile.add_argument("--file")
    p_add_profile.set_defaults(func=cmd_add_profile)

    p_delete_profile = subparsers.add_parser("delete-profile", help="Delete role profile")
    p_delete_profile.add_argument("role_id")
    p_delete_profile.set_defaults(func=cmd_delete_profile)

    p_add_memory = subparsers.add_parser("add-memory", help="Add or update memory slice")
    p_add_memory.add_argument("role_id")
    p_add_memory.add_argument("story_id")
    p_add_memory.add_argument("--text")
    p_add_memory.add_argument("--file")
    p_add_memory.set_defaults(func=cmd_add_memory)

    p_delete_memory = subparsers.add_parser("delete-memory", help="Delete one memory slice")
    p_delete_memory.add_argument("role_id")
    p_delete_memory.add_argument("story_id")
    p_delete_memory.set_defaults(func=cmd_delete_memory)

    p_delete_all_memory = subparsers.add_parser(
        "delete-all-memory",
        help="Delete all memory slices for one role",
    )
    p_delete_all_memory.add_argument("role_id")
    p_delete_all_memory.set_defaults(func=cmd_delete_all_memory)

    p_list_roles = subparsers.add_parser("list-roles", help="List available roles")
    p_list_roles.set_defaults(func=cmd_list_roles)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())