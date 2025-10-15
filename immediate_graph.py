"""
Immediate response graph for real-time interaction with the child.
"""
from langgraph.graph import StateGraph, START, END
from states import State
from nodes import (
    initialStateLoader,
    masterChatbot,
    format_response,
    immediate_graph_needs_initial_state,
    load_analysis
)


def create_immediate_response_graph(llm, memory, background_graph_instance):
    """
    Create and compile the immediate response graph.

    :param llm: Language model instance
    :param memory: Memory checkpointer
    :param background_graph_instance: Instance of background graph for loading analysis
    :return: Compiled graph
    """
    builder = StateGraph(State)

    # Add nodes with LLM binding
    builder.add_node("initialStateLoader", initialStateLoader)
    builder.add_node("load_analysis", lambda state: load_analysis(state, config, background_graph_instance))
    builder.add_node("masterChatbot", lambda state: masterChatbot(state, llm))
    builder.add_node("format_response", lambda state: format_response(state, llm))

    # Add edges
    builder.add_conditional_edges(START, immediate_graph_needs_initial_state)
    builder.add_edge("initialStateLoader", "load_analysis")
    builder.add_edge("load_analysis", "masterChatbot")
    builder.add_edge("masterChatbot", "format_response")
    builder.add_edge("format_response", END)

    return builder.compile(checkpointer=memory)


# Global config reference (will be set during execution)
config = None


def set_config(cfg):
    """Set the config for the graph."""
    global config
    config = cfg

