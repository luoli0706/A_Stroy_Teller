import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.chroma_memory import format_role_rag_context, index_memory_directory  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embedding and RAG index helper")
    parser.add_argument("command", choices=["index", "query"])
    parser.add_argument("--story-id", default="default")
    parser.add_argument("--roles", default="Reshaely,VanlyShan,SolinXuan")
    parser.add_argument("--target-role", default="Reshaely")
    parser.add_argument("--query", default="role memory retrieval")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--memory-dir", default="memory")
    parser.add_argument("--chroma-dir", default=".data/rag_chroma")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roles = [item.strip() for item in args.roles.split(",") if item.strip()]

    if args.command == "index":
        indexed = index_memory_directory(
            memory_dir=args.memory_dir,
            roles=roles,
            chroma_dir=args.chroma_dir,
        )
        print(f"Indexed memory documents: {indexed}")
        return 0

    context = format_role_rag_context(
        story_id=args.story_id,
        target_role_id=args.target_role,
        role_scope=roles,
        query_text=args.query,
        top_k=args.top_k,
        chroma_dir=args.chroma_dir,
    )
    print(context or "No RAG context found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
