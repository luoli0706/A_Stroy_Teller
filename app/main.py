from app.graph import build_graph


def main() -> None:
    graph = build_graph()

    result = graph.invoke(
        {
            "topic": "a traveler finding a hidden library",
            "style": "adventurous",
            "roles": ["alice", "bob"],
        }
    )

    print("=== Role Views ===")
    for role_id, draft in result.get("role_view_drafts", {}).items():
        print(f"\n--- {role_id} ---")
        print(draft)

    print("\n=== Integrated Story ===")
    print(result.get("final_story", ""))
    print(f"\nSaved run_id: {result.get('run_id', 'n/a')}")
    print(f"SQLite DB: {result.get('sqlite_db_path', '.data/story_teller.db')}")


if __name__ == "__main__":
    main()
