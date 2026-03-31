from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class StoryState(TypedDict):
    topic: str
    style: str
    draft: str


def write_draft(state: StoryState) -> StoryState:
    topic = state.get("topic", "an unexpected friendship")
    style = state.get("style", "warm")

    # Minimal placeholder node so the graph is runnable without external APIs.
    draft = (
        f"Once upon a time, there was a story about {topic}. "
        f"It was written in a {style} style and ended with hope."
    )

    return {**state, "draft": draft}


def build_graph():
    graph = StateGraph(StoryState)
    graph.add_node("write_draft", write_draft)
    graph.add_edge(START, "write_draft")
    graph.add_edge("write_draft", END)
    return graph.compile()
