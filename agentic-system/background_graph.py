"""
Background analysis graph for analyzing conversations asynchronously.
"""
from langgraph.graph import StateGraph, START, END
from states import BackgroundState
from nodes import (
    initialStateLoader,
    speechVocabularyWorker,
    speechGrammarWorker,
    speechInteractionWorker,
    speechComprehensionWorker,
    boredomWorker,
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
    builder.add_node("speechVocabularyWorker", lambda state, config: speechVocabularyWorker(state, config, llm))
    builder.add_node("speechGrammarWorker", lambda state, config: speechGrammarWorker(state, config, llm))
    builder.add_node("speechInteractionWorker", lambda state, config: speechInteractionWorker(state, config, llm))
    builder.add_node("speechComprehensionWorker", lambda state, config: speechComprehensionWorker(state, config, llm))
    builder.add_node("boredomWorker", lambda state, config: boredomWorker(state, config, llm))

    # Add edges
    builder.add_conditional_edges(START, background_graph_needs_initial_state)
    builder.add_edge("initialStateLoader", "speechVocabularyWorker")
    builder.add_edge("initialStateLoader", "speechGrammarWorker")
    builder.add_edge("initialStateLoader", "speechInteractionWorker")
    builder.add_edge("initialStateLoader", "speechComprehensionWorker")
    builder.add_edge("initialStateLoader", "boredomWorker")
    builder.add_edge("speechVocabularyWorker", END)
    builder.add_edge("speechGrammarWorker", END)
    builder.add_edge("speechInteractionWorker", END)
    builder.add_edge("speechComprehensionWorker", END)
    builder.add_edge("boredomWorker", END)

    return builder.compile(checkpointer=memory)
