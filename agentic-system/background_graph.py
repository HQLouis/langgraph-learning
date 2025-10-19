"""
Background analysis graph for analyzing conversations asynchronously.
"""
from langgraph.graph import StateGraph, START, END
from states import BackgroundState
from nodes import (
    initialStateLoader,
    educationalWorker,
    storytellingWorker,
    background_graph_needs_initial_state
)


def create_background_analysis_graph(llm, memory):
    """
    Create and compile the background analysis graph.

    :param llm: Language model instance
    :param memory: Memory checkpointer
    :return: Compiled graph
    """
    builder = StateGraph(BackgroundState)

    # Add nodes with LLM binding
    builder.add_node("initialStateLoader", initialStateLoader)
    builder.add_node("educationalWorker", lambda state, config: educationalWorker(state, config, llm))
    builder.add_node("storytellingWorker", lambda state, config: storytellingWorker(state, config, llm))

    # Add edges
    builder.add_conditional_edges(START, background_graph_needs_initial_state)
    builder.add_edge("initialStateLoader", "educationalWorker")
    builder.add_edge("initialStateLoader", "storytellingWorker")
    builder.add_edge("educationalWorker", END)
    builder.add_edge("storytellingWorker", END)

    return builder.compile(checkpointer=memory)

