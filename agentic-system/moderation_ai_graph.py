"""
Moderation AI graph for validating conversation compliance with system guidelines.
"""
from langgraph.graph import StateGraph, START, END
from states import ModerationState
from nodes import moderationWorker


def create_moderation_graph(llm, memory):
    """
    Create and compile the moderation AI graph.

    :param llm: Language model instance
    :param memory: Memory checkpointer
    :return: Compiled graph
    """
    builder = StateGraph(ModerationState)

    # Add moderation node with LLM binding
    builder.add_node("moderationWorker", lambda state, config: moderationWorker(state, config, llm))

    # Add edges - simple linear flow for now
    builder.add_edge(START, "moderationWorker")
    builder.add_edge("moderationWorker", END)

    return builder.compile(checkpointer=memory)

