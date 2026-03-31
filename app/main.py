import argparse

from app.graph import build_graph
from app.llm_client import get_story_client


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roles = [item.strip() for item in args.roles.split(",") if item.strip()]

    health = get_story_client().health_check()
    if not health.ok:
        raise SystemExit(f"Startup health check failed: {health.message}")

    graph = build_graph()

    result = graph.invoke(
        {
            "story_id": args.story_id,
            "topic": args.topic,
            "style": args.style,
            "roles": roles,
            "max_retry": args.max_retry,
        }
    )

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


if __name__ == "__main__":
    main()
