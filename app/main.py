from app.graph import build_graph


def main() -> None:
    graph = build_graph()

    result = graph.invoke(
        {
            "topic": "a traveler finding a hidden library",
            "style": "adventurous",
            "draft": "",
        }
    )

    print("=== Story Draft ===")
    print(result["draft"])


if __name__ == "__main__":
    main()
