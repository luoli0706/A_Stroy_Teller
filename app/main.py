import argparse
import json

from app.llm_client import get_story_client
from app.runtime import build_input_state, run_story, stream_story_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run A Story Teller graph")
    parser.add_argument("--story-id", default="urban_detective")
    parser.add_argument("--topic", default="a traveler finding a hidden library")
    parser.add_argument("--style", default="adventurous")
    parser.add_argument(
        "--roles",
        default="Reshaely,VanlyShan,SolinXuan",
        help="Comma-separated role IDs",
    )
    parser.add_argument("--max-retry", type=int, default=1)
    parser.add_argument(
        "--rag-enabled",
        choices=["true", "false"],
        default="true",
        help="Enable or disable RAG memory retrieval.",
    )
    parser.add_argument(
        "--rag-top-k",
        type=int,
        default=4,
        help="Top K retrieved memory slices per role for RAG context.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Output node updates as a stream (NDJSON style)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roles = [item.strip() for item in args.roles.split(",") if item.strip()]

    health = get_story_client().health_check()
    if not health.ok:
        raise SystemExit(f"Startup health check failed: {health.message}")

    state = build_input_state(
        story_id=args.story_id,
        topic=args.topic,
        style=args.style,
        roles=roles,
        max_retry=args.max_retry,
        rag_enabled=args.rag_enabled.lower() == "true",
        rag_top_k=args.rag_top_k,
    )

    if args.stream:
        final_result: dict = {}
        for event in stream_story_events(state):
            print(json.dumps(event, ensure_ascii=False))
            final_result.update(event.get("data", {}))
        result = final_result
    else:
        result = run_story(state)

    print("=== Role Views ===")
    for role_id, draft in result.get("role_view_drafts", {}).items():
        print(f"\n--- {role_id} ---")
        print(draft)

    print("\n=== Integrated Story ===")
    print(result.get("final_story", ""))

    print("\n=== Quality Report ===")
    print(result.get("quality_report", ""))

    print(f"\nSaved run_id: {result.get('run_id', 'n/a')}")
    print(f"SQLite DB: {result.get('sqlite_db_path', '.data/story_teller.db')}")
    print(f"Log File: {result.get('log_file_path', 'logs/run_<timestamp>.log')}")


if __name__ == "__main__":
    main()
